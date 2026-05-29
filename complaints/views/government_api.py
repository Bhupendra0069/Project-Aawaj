"""
AAWAJ Government API - Government-only endpoints.
Handles government dashboard data, actions, CSV export, and report downloads.
"""

import csv
import json

from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from ..models import Complaint, GovernmentAction
from ..serializers import ComplaintListSerializer, ComplaintDetailSerializer
from .helpers import role_required


@require_http_methods(["GET"])
@role_required('government')
def api_government_complaints(request):
    """Get complaints for government dashboard. Requires government role."""
    status_filter = request.GET.get('status', '')
    category = request.GET.get('category', '')
    priority = request.GET.get('priority', '')
    search = request.GET.get('search', '')

    complaints = Complaint.objects.filter(status__in=['published', 'resolved'])

    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category and category != 'all':
        complaints = complaints.filter(category=category)
    if priority and priority != 'all':
        complaints = complaints.filter(priority=priority)
    if search:
        complaints = complaints.filter(
            Q(description__icontains=search) |
            Q(location_text__icontains=search) |
            Q(complaint_code__icontains=search)
        )

    serializer = ComplaintListSerializer(complaints, many=True, context={'request': request})

    stats = {
        'total_active': Complaint.objects.filter(status='published').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
        'critical': Complaint.objects.filter(
            status='published', priority='critical'
        ).count(),
        'high_priority': Complaint.objects.filter(
            status='published', priority='high'
        ).count(),
    }

    return JsonResponse({'complaints': serializer.data, 'stats': stats})


@require_http_methods(["GET"])
@role_required('government')
def api_government_detail(request, complaint_id):
    """Get full complaint details for government. Requires government role."""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    serializer = ComplaintDetailSerializer(complaint, context={'request': request})
    return JsonResponse(serializer.data)


@csrf_exempt
@require_http_methods(["POST"])
@role_required('government')
def api_government_action(request, complaint_id):
    """Government takes action on a complaint. Requires government role."""
    try:
        complaint = get_object_or_404(Complaint, id=complaint_id)
        data = json.loads(request.body)

        action_type = data.get('action_type', '')
        notes = data.get('notes', '')
        officer_name = data.get('officer_name', request.user.get_full_name() or request.user.username)
        department = data.get('department', '')

        valid_actions = ['acknowledged', 'in_progress', 'resolved', 'referred']
        if action_type not in valid_actions:
            return JsonResponse({'error': 'Invalid action type'}, status=400)

        GovernmentAction.objects.create(
            complaint=complaint,
            action_type=action_type,
            notes=notes,
            officer_name=officer_name,
            department=department
        )

        if action_type == 'resolved':
            complaint.status = 'resolved'
            complaint.save()

        return JsonResponse({
            'success': True,
            'message': f'Action recorded for {complaint.complaint_code}',
            'new_status': complaint.get_status_display()
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@role_required('government')
def api_government_export_csv(request):
    """Export all government-visible complaints as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="aawaj_complaints_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Complaint Code', 'Category', 'Priority', 'Status', 'Location',
        'Latitude', 'Longitude', 'Ward', 'Description', 'AI Verdict',
        'AI Confidence', 'Severity', 'Urgent', 'Trust Score', 'Date'
    ])

    complaints = Complaint.objects.filter(status__in=['published', 'resolved']).order_by('-created_at')

    category = request.GET.get('category', '')
    priority = request.GET.get('priority', '')
    if category and category != 'all':
        complaints = complaints.filter(category=category)
    if priority and priority != 'all':
        complaints = complaints.filter(priority=priority)

    for c in complaints:
        writer.writerow([
            c.complaint_code,
            c.get_category_display(),
            c.get_priority_display(),
            c.get_status_display(),
            c.location_text,
            c.latitude,
            c.longitude,
            c.ward,
            c.description[:200],
            c.ai_verdict,
            c.ai_confidence_score,
            c.ai_severity_score,
            'Yes' if c.ai_urgency else 'No',
            c.trust_score,
            c.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


@require_http_methods(["GET"])
@role_required('government')
def api_government_download_report(request, complaint_id):
    """Download the AI-generated report for a specific complaint as a text file."""
    complaint = get_object_or_404(Complaint, id=complaint_id)

    report_text = complaint.ai_generated_report or 'No AI report generated for this complaint.'

    full_report = f"""AAWAJ COMPLAINT REPORT
Complaint Code: {complaint.complaint_code}
Date: {complaint.created_at.strftime('%Y-%m-%d %H:%M')}
Status: {complaint.get_status_display()}

{report_text}

--- END OF REPORT ---
"""

    response = HttpResponse(full_report, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="report_{complaint.complaint_code}.txt"'
    return response
