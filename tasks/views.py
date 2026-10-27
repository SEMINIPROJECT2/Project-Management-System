import csv
import json
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from accounts.models import User
from audit.services import log_audit_event
from notifications.services import send_notification
from projects.models import Membership, Project
from projects.permissions import require_project_membership
from .models import Task, TimeEntry, Comment

def parse_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_optional_date(value):
    """Return a date for a supplied ISO value, None for blank, or False if invalid."""
    if value in (None, ''):
        return None
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value
    return parse_date(str(value)) or False

@require_project_membership()
@require_http_methods(['GET', 'POST'])
def task_list_create_view(request, project_id):
    """
    SRS FR-05 & TC-05: Task creation and validation.
    SRS FR-08 & TC-08: Board multi-filtering.
    SRS FR-14 & TC-12: Task search scoped to project.
    """
    project = request.project
    membership = request.membership
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if request.method == 'POST':
        # FR-05 / SR-01 / TC-05: Only Owner or Manager can create tasks
        if membership.role not in [Membership.ROLE_OWNER, Membership.ROLE_MANAGER]:
            msg = "Only the Project Owner or Manager can create tasks."
            if is_json:
                return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': msg}}, status=403)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': {'code': 'INVALID_JSON', 'message': 'Invalid JSON body'}}, status=400)
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            priority = data.get('priority', Task.PRIORITY_MEDIUM)
            assignee_id = data.get('assignee_id')
            estimate_raw = data.get('estimate_hours', 0)
            due_date_raw = data.get('due_date')
        else:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            priority = request.POST.get('priority', Task.PRIORITY_MEDIUM)
            assignee_id = request.POST.get('assignee_id') or None
            estimate_raw = request.POST.get('estimate_hours', 0)
            due_date_raw = request.POST.get('due_date')

        # Validate required title (FR-05 / TC-05, SR-04)
        if not title:
            msg = "Task title is required."
            if is_json:
                return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': msg}}, status=400)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        if len(title) > 255:
            msg = "Task title cannot exceed 255 characters."
            if is_json:
                return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': msg}}, status=400)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        valid_priorities = [p[0] for p in Task.PRIORITY_CHOICES]
        if priority not in valid_priorities:
            priority = Task.PRIORITY_MEDIUM

        # Validate estimate hours: nonnegative, 0.5-hr increments (FR-09 / TC-09)
        estimate_val = parse_decimal(estimate_raw)
        if estimate_val is None or estimate_val < 0 or (estimate_val * 2) % 1 != 0:
            msg = "Estimate must be a non-negative number in 0.5-hour increments."
            if is_json:
                return JsonResponse({'error': {'code': 'INVALID_ESTIMATE', 'message': msg}}, status=400)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        due_date = parse_optional_date(due_date_raw)
        if due_date is False:
            msg = "Due date must use YYYY-MM-DD format."
            if is_json:
                return JsonResponse({'error': {'code': 'INVALID_DATE', 'message': msg}}, status=400)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        assignee = None
        if assignee_id:
            try:
                # Ensure assignee is actually a member of this project (SR-01)
                assignee_membership = Membership.objects.get(project=project, user_id=assignee_id)
                assignee = assignee_membership.user
            except Membership.DoesNotExist:
                msg = "Assignee is not a member of this project."
                if is_json:
                    return JsonResponse({'error': {'code': 'INVALID_ASSIGNEE', 'message': msg}}, status=400)
                messages.error(request, msg)
                return redirect('projects:project_detail', project_id=project.id)

        with transaction.atomic():
            task = Task.objects.create(
                project=project,
                title=title,
                description=description,
                assignee=assignee,
                status=Task.STATUS_BACKLOG,
                priority=priority,
                estimate_hours=estimate_val,
                due_date=due_date,
                version=1
            )
            # Log audit event (FR-13)
            log_audit_event(
                project=project,
                actor=request.user,
                action='TASK_CREATED',
                entity_type='Task',
                entity_id=task.id,
                details=f"Created task #{task.id}: '{task.title}' in Backlog"
            )
            # In-app notification to assignee (FR-17 / TC-14)
            if assignee and assignee != request.user:
                send_notification(
                    recipient=assignee,
                    title=f"New Task Assigned: #{task.id}",
                    message=f"You have been assigned to task #{task.id} '{task.title}' in {project.name}.",
                    link=f"/projects/{project.id}/"
                )

        if is_json:
            return JsonResponse({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'priority': task.priority,
                'estimate_hours': str(task.estimate_hours),
                'actual_hours': str(task.actual_hours),
                'version': task.version,
                'assignee': task.assignee.email if task.assignee else None,
                'message': 'Task created successfully in Backlog'
            }, status=201)

        messages.success(request, f"Task '{task.title}' created.")
        return redirect('projects:project_detail', project_id=project.id)

    # GET: Filter and Search tasks
    tasks_qs = Task.objects.filter(project=project).select_related('assignee')

    # Search by title or ID (FR-14 / TC-12)
    q = request.GET.get('q', '').strip()
    if q:
        if q.isdigit():
            tasks_qs = tasks_qs.filter(id=int(q))
        else:
            tasks_qs = tasks_qs.filter(title__icontains=q)

    # Multi-Filter (FR-08 / TC-08): Assignee, Priority, Due Status (Intersection only)
    assignee_filter = request.GET.get('assignee')
    if assignee_filter:
        if assignee_filter == 'unassigned':
            tasks_qs = tasks_qs.filter(assignee__isnull=True)
        elif assignee_filter.isdigit():
            tasks_qs = tasks_qs.filter(assignee_id=int(assignee_filter))

    priority_filter = request.GET.get('priority')
    if priority_filter:
        tasks_qs = tasks_qs.filter(priority=priority_filter)

    due_filter = request.GET.get('due_status')
    today = timezone.now().date()
    if due_filter == 'overdue':
        tasks_qs = tasks_qs.filter(due_date__lt=today).exclude(status=Task.STATUS_DONE)
    elif due_filter == 'due_today':
        tasks_qs = tasks_qs.filter(due_date=today)
    elif due_filter == 'due_future':
        tasks_qs = tasks_qs.filter(due_date__gt=today)

    data = [
        {
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'status': t.status,
            'priority': t.priority,
            'estimate_hours': str(t.estimate_hours),
            'actual_hours': str(t.actual_hours),
            'due_date': t.due_date.isoformat() if t.due_date else None,
            'is_overdue': t.is_overdue,
            'version': t.version,
            'assignee_id': t.assignee.id if t.assignee else None,
            'assignee_email': t.assignee.email if t.assignee else None,
            'assignee_name': t.assignee.full_name if t.assignee else None,
        }
        for t in tasks_qs
    ]
    return JsonResponse({'tasks': data})


@require_project_membership()
@require_http_methods(['GET', 'PUT', 'PATCH', 'POST'])
def task_detail_view(request, project_id, task_id):
    """
    SRS FR-06 & TC-06: Task editing and permission enforcement.
    Owner/Manager: Edit all fields.
    Member: Edit only assigned tasks, excluding assignee and estimate.
    Forbidden field changes rejected with 403.
    """
    project = request.project
    membership = request.membership
    task = get_object_or_404(Task, id=task_id, project=project)
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if request.method == 'GET':
        comments = [
            {
                'id': c.id,
                'author': c.author.email,
                'text': c.text,
                'created_at': c.created_at.isoformat()
            }
            for c in task.comments.all()
        ]
        time_entries = [
            {
                'id': te.id,
                'user': te.user.email,
                'hours': str(te.hours),
                'date': te.date.isoformat(),
                'note': te.note,
                'is_owner': te.user == request.user
            }
            for te in task.time_entries.all()
        ]
        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'estimate_hours': str(task.estimate_hours),
            'actual_hours': str(task.actual_hours),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'is_overdue': task.is_overdue,
            'version': task.version,
            'assignee_id': task.assignee.id if task.assignee else None,
            'assignee_email': task.assignee.email if task.assignee else None,
            'comments': comments,
            'time_entries': time_entries,
        })

    # Mutation: Edit Task
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': {'code': 'INVALID_JSON', 'message': 'Invalid JSON body'}}, status=400)
    else:
        data = request.POST

    # Permission checks (FR-06 / SR-01 / TC-06)
    is_owner_or_manager = membership.role in [Membership.ROLE_OWNER, Membership.ROLE_MANAGER]
    is_assigned_member = (membership.role == Membership.ROLE_MEMBER and task.assignee == request.user)

    if not is_owner_or_manager and not is_assigned_member:
        return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': 'You can only edit tasks assigned to you'}}, status=403)

    # If Member: forbidden from changing assignee and estimate
    if not is_owner_or_manager:
        if 'estimate_hours' in data or 'assignee_id' in data:
            return JsonResponse({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Members cannot alter task estimate or assignee'
                }
            }, status=403)

    with transaction.atomic():
        if 'title' in data:
            title = str(data['title']).strip()
            if not title:
                return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': 'Title cannot be blank'}}, status=400)
            task.title = title

        if 'description' in data:
            task.description = str(data['description']).strip()

        if 'priority' in data and is_owner_or_manager:
            task.priority = data['priority']

        if 'due_date' in data:
            due_date = parse_optional_date(data['due_date'])
            if due_date is False:
                return JsonResponse({'error': {'code': 'INVALID_DATE', 'message': 'Due date must use YYYY-MM-DD format'}}, status=400)
            task.due_date = due_date

        if is_owner_or_manager and 'estimate_hours' in data:
            est_val = parse_decimal(data['estimate_hours'])
            if est_val is None or est_val < 0 or (est_val * 2) % 1 != 0:
                return JsonResponse({'error': {'code': 'INVALID_ESTIMATE', 'message': 'Estimate must be non-negative 0.5 increment'}}, status=400)
            task.estimate_hours = est_val

        if is_owner_or_manager and 'assignee_id' in data:
            new_assignee_id = data['assignee_id']
            if new_assignee_id:
                try:
                    target_member = Membership.objects.get(project=project, user_id=new_assignee_id)
                    task.assignee = target_member.user
                    # In-app notification
                    if task.assignee != request.user:
                        send_notification(
                            recipient=task.assignee,
                            title=f"Task Assignment Update: #{task.id}",
                            message=f"You are assigned to task #{task.id} '{task.title}' in {project.name}.",
                            link=f"/projects/{project.id}/"
                        )
                except Membership.DoesNotExist:
                    return JsonResponse({'error': {'code': 'INVALID_ASSIGNEE', 'message': 'Assignee is not in project'}}, status=400)
            else:
                task.assignee = None

        task.version += 1
        task.save()

        log_audit_event(
            project=project,
            actor=request.user,
            action='TASK_EDITED',
            entity_type='Task',
            entity_id=task.id,
            details=f"Task #{task.id} updated (version {task.version})"
        )

    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'status': task.status,
        'version': task.version,
        'estimate_hours': str(task.estimate_hours),
        'assignee': task.assignee.email if task.assignee else None,
        'message': 'Task updated successfully'
    })


@require_project_membership()
@require_http_methods(['PATCH', 'POST'])
def task_status_transition_view(request, project_id, task_id):
    """
    SRS FR-07 & TC-07: Kanban workflow transitions.
    Transitions task among Backlog, To Do, In Progress, Review, Done.
    SAD §3.7 & §4.3: Concurrency protection using expected_version.
    Returns 409 Conflict if expected_version does not match current version.
    """
    project = request.project
    task = get_object_or_404(Task, id=task_id, project=project)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    new_status = data.get('status')
    valid_statuses = [Task.STATUS_BACKLOG, Task.STATUS_TODO, Task.STATUS_IN_PROGRESS, Task.STATUS_REVIEW, Task.STATUS_DONE]
    if new_status not in valid_statuses:
        return JsonResponse({'error': {'code': 'INVALID_STATUS', 'message': f'Invalid status: {new_status}'}}, status=400)

    # Concurrency check (SAD §3.7 / §4.3)
    expected_version = data.get('expected_version')
    if expected_version is not None:
        try:
            if int(expected_version) != task.version:
                return JsonResponse({
                    'error': {
                        'code': 'CONFLICT',
                        'message': f'Stale version: expected {expected_version}, but task is at version {task.version}. Please refresh.'
                    }
                }, status=409)
        except ValueError:
            return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': 'expected_version must be integer'}}, status=400)

    with transaction.atomic():
        old_status = task.status
        task.status = new_status
        task.version += 1
        task.save(update_fields=['status', 'version', 'updated_at'])

        # Record transition in audit trail (FR-07 / FR-13 / TC-07)
        log_audit_event(
            project=project,
            actor=request.user,
            action='TASK_MOVED',
            entity_type='Task',
            entity_id=task.id,
            details=f"Moved task #{task.id} from '{old_status}' to '{new_status}'"
        )

    return JsonResponse({
        'id': task.id,
        'status': task.status,
        'version': task.version,
        'message': f"Status changed to {task.status}"
    })


@require_project_membership()
@require_POST
def task_time_log_view(request, project_id, task_id):
    """
    SRS FR-10 & TC-10: Time logging.
    Positive time in 0.25-hour increments with date and note.
    Actual hours recomputed automatically.
    """
    project = request.project
    task = get_object_or_404(Task, id=task_id, project=project)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    hours_val = parse_decimal(data.get('hours'))
    # Must be positive and in 0.25-hr increments (FR-10 / TC-10)
    if hours_val is None or hours_val <= 0 or (hours_val * 4) % 1 != 0:
        return JsonResponse({
            'error': {
                'code': 'INVALID_HOURS',
                'message': 'Hours must be a positive number in 0.25-hour increments (e.g. 0.25, 0.5, 0.75, 1.25)'
            }
        }, status=400)

    date_raw = data.get('date')
    date_val = parse_optional_date(date_raw) if date_raw else timezone.now().date()
    if date_val is False:
        return JsonResponse({
            'error': {
                'code': 'INVALID_DATE',
                'message': 'Date must use YYYY-MM-DD format'
            }
        }, status=400)
    note = data.get('note', '').strip()

    with transaction.atomic():
        entry = TimeEntry.objects.create(
            task=task,
            user=request.user,
            hours=hours_val,
            date=date_val,
            note=note
        )
        log_audit_event(
            project=project,
            actor=request.user,
            action='TIME_LOGGED',
            entity_type='TimeEntry',
            entity_id=entry.id,
            details=f"Logged {entry.hours}h on task #{task.id}"
        )

    return JsonResponse({
        'entry_id': entry.id,
        'task_id': task.id,
        'hours': str(entry.hours),
        'actual_hours': str(task.actual_hours),
        'message': 'Time logged successfully'
    }, status=201)


@require_project_membership()
@require_http_methods(['PUT', 'POST', 'DELETE'])
def time_entry_detail_view(request, project_id, task_id, entry_id):
    """
    SRS FR-10: Members can edit/delete only their own time entries.
    """
    project = request.project
    task = get_object_or_404(Task, id=task_id, project=project)
    entry = get_object_or_404(TimeEntry, id=entry_id, task=task)

    if entry.user != request.user:
        return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': 'You can only edit your own time logs'}}, status=403)

    if request.method == 'DELETE':
        with transaction.atomic():
            entry.delete()
            log_audit_event(
                project=project,
                actor=request.user,
                action='TIME_DELETED',
                entity_type='TimeEntry',
                entity_id=entry_id,
                details=f"Deleted time entry on task #{task.id}"
            )
        return JsonResponse({'success': True, 'actual_hours': str(task.actual_hours)})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    hours_val = parse_decimal(data.get('hours'))
    if hours_val is None or hours_val <= 0 or (hours_val * 4) % 1 != 0:
        return JsonResponse({'error': {'code': 'INVALID_HOURS', 'message': 'Hours must be positive in 0.25 increments'}}, status=400)

    with transaction.atomic():
        entry.hours = hours_val
        if 'note' in data:
            entry.note = data['note']
        entry.save()
        log_audit_event(
            project=project,
            actor=request.user,
            action='TIME_UPDATED',
            entity_type='TimeEntry',
            entity_id=entry.id,
            details=f"Updated time entry to {entry.hours}h on task #{task.id}"
        )

    return JsonResponse({
        'entry_id': entry.id,
        'hours': str(entry.hours),
        'actual_hours': str(task.actual_hours),
        'message': 'Time entry updated'
    })


@require_project_membership()
@require_POST
def task_comment_create_view(request, project_id, task_id):
    """
    SRS FR-12 & TC-12: Task comments in chronological order.
    """
    project = request.project
    task = get_object_or_404(Task, id=task_id, project=project)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': 'Comment text cannot be empty'}}, status=400)

    with transaction.atomic():
        comment = Comment.objects.create(
            task=task,
            author=request.user,
            text=text
        )
        log_audit_event(
            project=project,
            actor=request.user,
            action='COMMENT_ADDED',
            entity_type='Comment',
            entity_id=comment.id,
            details=f"Added comment on task #{task.id}"
        )

    return JsonResponse({
        'id': comment.id,
        'author': comment.author.email,
        'text': comment.text,
        'created_at': comment.created_at.isoformat(),
        'message': 'Comment added successfully'
    }, status=201)


@require_project_membership()
@require_GET
def project_dashboard_api(request, project_id):
    """
    SRS FR-11 & TC-11: Progress visibility dashboard.
    Returns status counts, overdue count, estimated hours, and actual hours.
    """
    project = request.project
    tasks = Task.objects.filter(project=project)

    status_counts = {
        Task.STATUS_BACKLOG: 0,
        Task.STATUS_TODO: 0,
        Task.STATUS_IN_PROGRESS: 0,
        Task.STATUS_REVIEW: 0,
        Task.STATUS_DONE: 0,
    }
    for item in tasks.values('status').annotate(count=models.Count('id')):
        status_counts[item['status']] = item['count']

    today = timezone.now().date()
    overdue_count = tasks.filter(due_date__lt=today).exclude(status=Task.STATUS_DONE).count()

    total_estimated = tasks.aggregate(models.Sum('estimate_hours'))['estimate_hours__sum'] or Decimal('0.00')
    total_actual = TimeEntry.objects.filter(task__project=project).aggregate(models.Sum('hours'))['hours__sum'] or Decimal('0.00')

    return JsonResponse({
        'status_counts': status_counts,
        'overdue_count': overdue_count,
        'total_tasks': tasks.count(),
        'estimated_hours': f"{Decimal(str(total_estimated)):.2f}",
        'actual_hours': f"{Decimal(str(total_actual)):.2f}",
    })


@require_project_membership(allowed_roles=[Membership.ROLE_OWNER, Membership.ROLE_MANAGER])
@require_GET
def project_tasks_csv_view(request, project_id):
    """
    SRS FR-15 & TC-13: CSV task export.
    Only Owner or Manager can download CSV containing:
    ID, title, status, assignee, estimate, actual_hours, due_date.
    """
    project = request.project
    tasks = Task.objects.filter(project=project).select_related('assignee').order_by('id')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{project.name.replace(" ", "_")}_tasks.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Status', 'Assignee', 'Estimate (Hours)', 'Actual Hours', 'Due Date'])

    for t in tasks:
        writer.writerow([
            t.id,
            t.title,
            t.status,
            t.assignee.email if t.assignee else 'Unassigned',
            t.estimate_hours,
            t.actual_hours,
            t.due_date.isoformat() if t.due_date else 'None'
        ])

    return response
