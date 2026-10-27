"""
Centralized Server-side Authorization Service.
SRS SR-01, FR-04, FR-06, FR-16.
Architecture Design Section 3.4 & 3.9.
"""
from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
from .models import Project, Membership

def get_user_project_membership(user, project_id):
    """Retrieve membership if exists and user is authenticated."""
    if not user.is_authenticated:
        return None
    try:
        return Membership.objects.select_related('project', 'user').get(
            project_id=project_id,
            user=user
        )
    except Membership.DoesNotExist:
        return None

def require_project_membership(allowed_roles=None, allow_archived_mutation=False):
    """
    Decorator enforcing:
    1. User is authenticated (401).
    2. User is a member of the project (404 to avoid leaking project existence).
    3. User has one of the allowed roles (403).
    4. If project is archived, state-changing requests return 409 Conflict (FR-16, SAD §4.4).
    """
    if allowed_roles is None:
        allowed_roles = [Membership.ROLE_OWNER, Membership.ROLE_MANAGER, Membership.ROLE_MEMBER]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, project_id, *args, **kwargs):
            is_json = (
                request.content_type == 'application/json'
                or 'application/json' in request.headers.get('Accept', '')
                or 'application/json' in request.META.get('HTTP_ACCEPT', '')
                or request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or (request.path.startswith('/tasks/projects/') and not request.path.endswith('.csv'))
            )

            if not request.user.is_authenticated:
                if is_json:
                    return JsonResponse({'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required'}}, status=401)
                return redirect('accounts:login')

            membership = get_user_project_membership(request.user, project_id)
            if not membership:
                if is_json:
                    return JsonResponse({'error': {'code': 'NOT_FOUND', 'message': 'Project not found or access denied'}}, status=404)
                return render(request, '404.html', {'message': 'Project not found or access denied'}, status=404)

            project = membership.project

            # Role check (SR-01)
            if membership.role not in allowed_roles:
                if is_json:
                    return JsonResponse({'error': {'code': 'FORBIDDEN', 'message': f'Access denied: requires role in {allowed_roles}'}}, status=403)
                return render(request, '403.html', {'message': 'You do not have permission for this action'}, status=403)

            # Archival check (FR-16 / TC-13 / SAD §4.4)
            if project.is_archived and request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and not allow_archived_mutation:
                msg = "Project is archived and read-only. Modifications are rejected."
                if is_json:
                    return JsonResponse({'error': {'code': 'PROJECT_ARCHIVED', 'message': msg}}, status=409)
                return render(request, '409.html', {'message': msg}, status=409)

            request.membership = membership
            request.project = project
            return view_func(request, project_id, *args, **kwargs)
        return _wrapped_view
    return decorator
