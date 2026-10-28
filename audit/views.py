from django.http import JsonResponse
from django.shortcuts import render
from projects.permissions import require_project_membership
from .models import ActivityEvent

@require_project_membership()
def project_activity_api(request, project_id):
    """
    SRS FR-13: Retrieve activity history for a project in time order.
    Scoped strictly to authorized project members.
    """
    events = ActivityEvent.objects.filter(project_id=project_id).select_related('actor').order_by('-created_at', '-id')
    data = [
        {
            'id': event.id,
            'actor': event.actor.email if event.actor else 'System',
            'action': event.action,
            'entity_type': event.entity_type,
            'entity_id': event.entity_id,
            'details': event.details,
            'created_at': event.created_at.isoformat(),
        }
        for event in events
    ]
    return JsonResponse({'events': data})
