"""
AAWAJ Moderation API - Moderator-only endpoints.
Handles moderation queue, approve/reject actions, and contact message management.
"""

import json

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from ..models import Complaint, ModerationLog, ContactMessage
from ..serializers import ComplaintListSerializer, ComplaintDetailSerializer
from .helpers import role_required


@require_http_methods(["GET"])
@role_required('moderator')
def api_moderation_queue(request):
    """Get complaints pending moderation. Requires moderator role."""
    status_filter = request.GET.get('status', 'pending_review')
    complaints = Complaint.objects.filter(status=status_filter)

    serializer = ComplaintListSerializer(complaints, many=True, context={'request': request})
    
    stats = {
        'pending': Complaint.objects.filter(status='pending_review').count(),
        'published': Complaint.objects.filter(status='published').count(),
        'rejected': Complaint.objects.filter(status='rejected').count(),
        'total_today': Complaint.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
    }

    return JsonResponse({'complaints': serializer.data, 'stats': stats})


@csrf_exempt
@require_http_methods(["POST"])
@role_required('moderator')
def api_moderation_action(request, complaint_id):
    """Approve or reject a complaint. Requires moderator role."""
    try:
        complaint = get_object_or_404(Complaint, id=complaint_id)
        data = json.loads(request.body)
        action = data.get('action', '')
        notes = data.get('notes', '')

        if action not in ('approve', 'reject'):
            return JsonResponse({'error': 'Invalid action'}, status=400)

        ModerationLog.objects.create(
            complaint=complaint,
            moderator=request.user,
            action=action,
            notes=notes
        )

        if action == 'approve':
            complaint.status = 'published'
        elif action == 'reject':
            complaint.status = 'rejected'

        complaint.save()

        return JsonResponse({
            'success': True,
            'new_status': complaint.get_status_display(),
            'message': f'Complaint {complaint.complaint_code} has been {action}d.'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@role_required('moderator')
def api_moderation_detail(request, complaint_id):
    """Get full complaint details for moderation. Requires moderator role."""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    serializer = ComplaintDetailSerializer(complaint, context={'request': request})
    return JsonResponse(serializer.data)


@require_http_methods(["GET"])
@role_required('moderator')
def api_contact_messages(request):
    """Get all contact messages for moderators."""
    filter_type = request.GET.get('filter', 'all')
    messages = ContactMessage.objects.all().order_by('-created_at')

    if filter_type == 'unread':
        messages = messages.filter(is_read=False)
    elif filter_type == 'read':
        messages = messages.filter(is_read=True)

    data = [{
        'id': m.id,
        'name': m.name,
        'email': m.email,
        'subject': m.subject,
        'message': m.message,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat(),
    } for m in messages]

    unread_count = ContactMessage.objects.filter(is_read=False).count()
    total_count = ContactMessage.objects.count()

    return JsonResponse({
        'messages': data,
        'unread_count': unread_count,
        'total_count': total_count,
    })


@csrf_exempt
@require_http_methods(["POST"])
@role_required('moderator')
def api_contact_mark_read(request, message_id):
    """Mark a contact message as read."""
    try:
        msg = get_object_or_404(ContactMessage, id=message_id)
        msg.is_read = True
        msg.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
