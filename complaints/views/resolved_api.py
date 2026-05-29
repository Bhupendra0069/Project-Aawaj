"""
AAWAJ Public API - Resolved cases endpoint.
Provides resolved complaint data with resolution details for the public resolved cases page.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Avg
from django.utils import timezone
from datetime import timedelta

from ..models import Complaint, GovernmentAction
from ..serializers import ComplaintListSerializer


@require_http_methods(["GET"])
def api_resolved_cases(request):
    """Get all resolved complaints with resolution details for public view."""
    category = request.GET.get('category', 'all')
    search = request.GET.get('search', '')

    complaints = Complaint.objects.filter(status='resolved').order_by('-updated_at')

    if category and category != 'all':
        complaints = complaints.filter(category=category)
    if search:
        complaints = complaints.filter(
            Q(description__icontains=search) |
            Q(location_text__icontains=search) |
            Q(complaint_code__icontains=search)
        )

    # Serialize with resolution data
    cases = []
    all_departments = set()

    for c in complaints:
        # Get first image
        first_img = c.images.first()
        first_image_url = ''
        if first_img and first_img.image:
            try:
                first_image_url = first_img.image.url
            except Exception:
                first_image_url = ''

        # Get resolution action (the 'resolved' government action)
        resolved_action = c.government_actions.filter(action_type='resolved').first()
        # Get publish/approval date from moderation logs
        publish_log = c.moderation_logs.filter(action='approve').first()

        published_date = publish_log.created_at.isoformat() if publish_log else c.created_at.isoformat()
        resolved_date = resolved_action.created_at.isoformat() if resolved_action else c.updated_at.isoformat()
        resolved_by = resolved_action.officer_name if resolved_action else ''
        resolved_department = resolved_action.department if resolved_action else ''

        if resolved_department:
            all_departments.add(resolved_department)

        # Calculate days to resolve
        pub_dt = publish_log.created_at if publish_log else c.created_at
        res_dt = resolved_action.created_at if resolved_action else c.updated_at
        days_to_resolve = max(0, (res_dt - pub_dt).days)

        cases.append({
            'complaint_code': c.complaint_code,
            'description': c.description or '',
            'location_text': c.location_text,
            'category': c.category,
            'priority': c.priority,
            'status': c.status,
            'created_at': c.created_at.isoformat(),
            'first_image': first_image_url,
            'published_date': published_date,
            'resolved_date': resolved_date,
            'resolved_by': resolved_by,
            'resolved_department': resolved_department,
            'days_to_resolve': days_to_resolve,
            'ai_severity_score': c.ai_severity_score,
        })

    # Stats
    total_resolved = Complaint.objects.filter(status='resolved').count()
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resolved_this_month = Complaint.objects.filter(
        status='resolved', updated_at__gte=month_start
    ).count()

    # Average resolution days
    avg_days_list = [c['days_to_resolve'] for c in cases if c['days_to_resolve'] is not None]
    avg_resolution_days = round(sum(avg_days_list) / len(avg_days_list), 1) if avg_days_list else 0

    return JsonResponse({
        'cases': cases,
        'count': len(cases),
        'stats': {
            'total_resolved': total_resolved,
            'resolved_this_month': resolved_this_month,
            'avg_resolution_days': avg_resolution_days,
            'departments_involved': len(all_departments) or 1,
        }
    })
