import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from accounts.models import User
from audit.services import log_audit_event
from notifications.services import send_notification
from .models import Project, Membership
from .permissions import require_project_membership

@login_required
@require_http_methods(['GET', 'POST'])
def project_list_view(request):
    """
    SRS FR-03 & TC-03: List projects and create a new project.
    Creator becomes the Owner of the newly created project.
    """
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': {'code': 'INVALID_JSON', 'message': 'Invalid JSON body'}}, status=400)
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            start_date = data.get('start_date') or timezone.now().date()
            target_date = data.get('target_date') or None
        else:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            start_date = request.POST.get('start_date') or timezone.now().date()
            target_date = request.POST.get('target_date') or None

        if not name:
            if is_json:
                return JsonResponse({'error': {'code': 'BAD_REQUEST', 'message': 'Project name is required'}}, status=400)
            messages.error(request, 'Project name is required.')
            return redirect('projects:project_list')

        with transaction.atomic():
            project = Project.objects.create(
                name=name,
                description=description,
                start_date=start_date,
                target_date=target_date,
                owner=request.user
            )
            # Creator becomes Owner
            Membership.objects.create(
                project=project,
                user=request.user,
                role=Membership.ROLE_OWNER
            )
            log_audit_event(
                project=project,
                actor=request.user,
                action='PROJECT_CREATED',
                entity_type='Project',
                entity_id=project.id,
                details=f"Project '{project.name}' created by {request.user.email} (Owner)"
            )

        if is_json:
            return JsonResponse({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'role': Membership.ROLE_OWNER,
                'is_archived': project.is_archived,
                'message': 'Project created successfully'
            }, status=201)

        messages.success(request, f"Project '{project.name}' created successfully.")
        return redirect('projects:project_detail', project_id=project.id)

    # GET: List all projects user is member of
    user_memberships = Membership.objects.filter(user=request.user).select_related('project', 'project__owner')
    projects_data = []
    for m in user_memberships:
        p = m.project
        projects_data.append({
            'project': p,
            'role': m.role,
            'is_archived': p.is_archived
        })

    if is_json:
        return JsonResponse({
            'projects': [
                {
                    'id': p['project'].id,
                    'name': p['project'].name,
                    'description': p['project'].description,
                    'role': p['role'],
                    'is_archived': p['is_archived'],
                    'created_at': p['project'].created_at.isoformat(),
                }
                for p in projects_data
            ]
        })

    return render(request, 'projects/list.html', {'projects_data': projects_data})


@require_project_membership()
def project_detail_view(request, project_id):
    """View project dashboard and Kanban board."""
    project = request.project
    membership = request.membership
    members = Membership.objects.filter(project=project).select_related('user')
    return render(request, 'projects/detail.html', {
        'project': project,
        'membership': membership,
        'members': members,
        'is_owner': membership.role == Membership.ROLE_OWNER,
        'is_manager_or_owner': membership.role in [Membership.ROLE_OWNER, Membership.ROLE_MANAGER],
    })


@require_project_membership(allowed_roles=[Membership.ROLE_OWNER], allow_archived_mutation=True)
@require_POST
def project_archive_view(request, project_id):
    """
    SRS FR-16 & TC-13: Project archiving.
    Only the Owner can archive a project.
    Archived projects are read-only.
    """
    project = request.project
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if project.is_archived:
        msg = "Project is already archived and read-only. Modifications are rejected."
        if is_json:
            return JsonResponse({'error': {'code': 'PROJECT_ALREADY_ARCHIVED', 'message': msg}}, status=409)
        messages.warning(request, msg)
        return redirect('projects:project_detail', project_id=project.id)

    with transaction.atomic():
        project.archived_at = timezone.now()
        project.save(update_fields=['archived_at'])
        log_audit_event(
            project=project,
            actor=request.user,
            action='PROJECT_ARCHIVED',
            entity_type='Project',
            entity_id=project.id,
            details=f"Project '{project.name}' was archived by {request.user.email}"
        )

    if is_json:
        return JsonResponse({
            'id': project.id,
            'name': project.name,
            'is_archived': True,
            'archived_at': project.archived_at.isoformat(),
            'message': 'Project archived successfully'
        })

    messages.info(request, f"Project '{project.name}' has been archived and is now read-only.")
    return redirect('projects:project_detail', project_id=project.id)


@require_project_membership()
@require_http_methods(['GET', 'POST'])
def project_members_view(request, project_id):
    """
    SRS FR-04 & TC-04 & FR-17 & TC-14:
    List members, or Owner invites an existing user by email.
    Sends notification to invited member.
    """
    project = request.project
    membership = request.membership
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if request.method == 'POST':
        # Only Owner can invite / add members (FR-04 / SR-01 / TC-04)
        if membership.role != Membership.ROLE_OWNER:
            msg = "Only the Project Owner can invite members or modify roles."
            if is_json:
                return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': msg}}, status=403)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': {'code': 'INVALID_JSON', 'message': 'Invalid JSON body'}}, status=400)
            email = data.get('email', '').strip().lower()
            role = data.get('role', Membership.ROLE_MEMBER)
        else:
            email = request.POST.get('email', '').strip().lower()
            role = request.POST.get('role', Membership.ROLE_MEMBER)

        if role not in [Membership.ROLE_OWNER, Membership.ROLE_MANAGER, Membership.ROLE_MEMBER]:
            return JsonResponse({'error': {'code': 'INVALID_ROLE', 'message': 'Invalid role specified'}}, status=400)

        try:
            target_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            msg = f"User with email '{email}' does not exist in the system."
            if is_json:
                return JsonResponse({'error': {'code': 'USER_NOT_FOUND', 'message': msg}}, status=404)
            messages.error(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        if Membership.objects.filter(project=project, user=target_user).exists():
            msg = "User is already a member of this project."
            if is_json:
                return JsonResponse({'error': {'code': 'ALREADY_MEMBER', 'message': msg}}, status=400)
            messages.warning(request, msg)
            return redirect('projects:project_detail', project_id=project.id)

        with transaction.atomic():
            new_membership = Membership.objects.create(project=project, user=target_user, role=role)
            # Log audit event (FR-13)
            log_audit_event(
                project=project,
                actor=request.user,
                action='MEMBER_INVITED',
                entity_type='Membership',
                entity_id=new_membership.id,
                details=f"Invited {target_user.email} as {role}"
            )
            # Send in-app notification (FR-17, TC-14)
            send_notification(
                recipient=target_user,
                title=f"Invited to {project.name}",
                message=f"You have been added as {role} in project '{project.name}' by {request.user.email}.",
                link=f"/projects/{project.id}/"
            )

        if is_json:
            return JsonResponse({
                'id': new_membership.id,
                'email': target_user.email,
                'role': new_membership.role,
                'message': 'Member invited successfully'
            }, status=201)

        messages.success(request, f"Invited {target_user.email} as {role}.")
        return redirect('projects:project_detail', project_id=project.id)

    # GET members
    members = Membership.objects.filter(project=project).select_related('user')
    data = [
        {
            'id': m.id,
            'user_id': m.user.id,
            'email': m.user.email,
            'full_name': m.user.full_name,
            'role': m.role,
        }
        for m in members
    ]
    return JsonResponse({'members': data})


@require_project_membership()
@require_POST
def project_member_role_update_view(request, project_id, member_user_id):
    """
    SRS FR-04 & TC-04:
    Only Owner shall change membership roles.
    A Member role-change attempt is denied with 403.
    """
    project = request.project
    membership = request.membership
    is_json = request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', '')

    if membership.role != Membership.ROLE_OWNER:
        msg = "Only the Project Owner can modify membership roles."
        if is_json:
            return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': msg}}, status=403)
        return render(request, '403.html', {'message': msg}, status=403)

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': {'code': 'INVALID_JSON', 'message': 'Invalid JSON body'}}, status=400)
        new_role = data.get('role')
    else:
        new_role = request.POST.get('role')

    if new_role not in [Membership.ROLE_OWNER, Membership.ROLE_MANAGER, Membership.ROLE_MEMBER]:
        return JsonResponse({'error': {'code': 'INVALID_ROLE', 'message': 'Invalid role'}}, status=400)

    target_membership = get_object_or_404(Membership, project=project, user_id=member_user_id)

    # The canonical project owner must always retain an Owner membership. Without
    # this guard, an owner could demote themselves and leave the project without a
    # stable administrative principal even though Project.owner still points to them.
    if target_membership.user_id == project.owner_id and new_role != Membership.ROLE_OWNER:
        return JsonResponse({
            'error': {
                'code': 'OWNER_ROLE_REQUIRED',
                'message': 'The project creator must retain the Owner role.'
            }
        }, status=400)

    with transaction.atomic():
        old_role = target_membership.role
        target_membership.role = new_role
        target_membership.save(update_fields=['role'])
        log_audit_event(
            project=project,
            actor=request.user,
            action='ROLE_CHANGED',
            entity_type='Membership',
            entity_id=target_membership.id,
            details=f"Changed role of {target_membership.user.email} from {old_role} to {new_role}"
        )

    if is_json:
        return JsonResponse({
            'user_id': member_user_id,
            'old_role': old_role,
            'new_role': new_role,
            'message': 'Role updated successfully'
        })
    messages.success(request, f"Updated role of {target_membership.user.email} to {new_role}.")
    return redirect('projects:project_detail', project_id=project.id)
