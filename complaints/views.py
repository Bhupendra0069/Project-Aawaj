"""
AAWAJ Views - API endpoints and template views.
Includes Phase 2 analytics API endpoints.
"""

import csv
import json
from functools import wraps

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Complaint, ComplaintImage, ComplaintAudio, ModerationLog,
    GovernmentAction, ContactMessage, ComplaintCluster
)
from .serializers import (
    ComplaintListSerializer, ComplaintDetailSerializer,
    ModerationLogSerializer, GovernmentActionSerializer
)
from . import ai_service


def role_required(*group_names):
    """
    Decorator that checks if the user belongs to any of the given groups.
    Returns 401/403 JSON for API views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            return JsonResponse({'error': 'Forbidden: insufficient permissions'}, status=403)
        return wrapper
    return decorator


def page_role_required(*group_names):
    """
    Decorator for template views that checks group membership.
    Redirects to login if not authenticated, shows 403 page if wrong role.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            return render(request, 'home.html', status=403)
        return wrapper
    return decorator


# ============================================================
# TEMPLATE VIEWS (Page rendering)
# ============================================================

def home_view(request):
    """Landing page."""
    return render(request, 'home.html')

def report_view(request):
    """Complaint submission page."""
    return render(request, 'report.html')

def track_view(request):
    """Track complaint status page."""
    return render(request, 'track.html')

def public_dashboard_view(request):
    """Public complaints dashboard."""
    return render(request, 'public_dashboard.html')

def map_view(request):
    """Complaint heatmap page."""
    return render(request, 'map.html')

def about_view(request):
    """About page."""
    return render(request, 'about.html')

def contact_view(request):
    """Contact page."""
    return render(request, 'contact.html')

def login_view(request):
    """Login page for moderators/government/admin."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect based on user group
            if user.groups.filter(name='government').exists():
                return JsonResponse({'success': True, 'redirect': '/government/'})
            elif user.groups.filter(name='moderator').exists():
                return JsonResponse({'success': True, 'redirect': '/moderation/'})
            else:
                return JsonResponse({'success': True, 'redirect': '/moderation/'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
    return render(request, 'login.html')

def logout_view(request):
    """Logout and redirect to home."""
    logout(request)
    from django.shortcuts import redirect
    return redirect('/')

@page_role_required('moderator')
def moderation_view(request):
    """Admin moderation panel. Requires moderator group."""
    return render(request, 'moderation.html')

@page_role_required('government')
def government_dashboard_view(request):
    """Government dashboard. Requires government group."""
    return render(request, 'government_dashboard.html')

@page_role_required('government')
def government_case_detail_view(request, complaint_id):
    """Government case detail page. Requires government group."""
    return render(request, 'government_case_detail.html', {'complaint_id': complaint_id})

@page_role_required('government')
def government_analytics_view(request):
    """Government analytics dashboard. Requires government group."""
    return render(request, 'government_analytics.html')


# ============================================================
# API VIEWS (JSON endpoints)
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_submit_complaint(request):
    """
    Submit a new complaint.
    Expects multipart form data with: images, location_text, latitude, longitude, description, audio
    """
    try:
        location_text = request.POST.get('location_text', '')
        latitude = float(request.POST.get('latitude', 27.7172))
        longitude = float(request.POST.get('longitude', 85.3240))
        description = request.POST.get('description', '')

        images = request.FILES.getlist('images')
        audio = request.FILES.get('audio')

        # Validation
        if not location_text:
            return JsonResponse({'error': 'Location is required'}, status=400)
        if not images:
            return JsonResponse({'error': 'At least one image is required'}, status=400)
        if not description and not audio:
            return JsonResponse({'error': 'Either text description or audio is required'}, status=400)

        # Auto-detect ward from coordinates
        from .services import geo_service
        ward = geo_service.detect_ward(latitude, longitude)

        # Create complaint
        complaint = Complaint.objects.create(
            description=description,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude,
            ward=ward,
            status='pending_ai'
        )

        # Save images
        for img in images:
            ComplaintImage.objects.create(complaint=complaint, image=img)

        # Save audio & transcribe
        if audio:
            audio_obj = ComplaintAudio.objects.create(
                complaint=complaint, audio_file=audio
            )
            # Mock transcription
            transcription = ai_service.transcribe_audio(audio)
            audio_obj.transcription = transcription
            audio_obj.save()

            # If no text description, use transcription
            if not description:
                complaint.description = transcription
                complaint.save()

        # Run AI analysis
        ai_results = ai_service.process_complaint(complaint)

        # Update complaint with AI results
        for key, value in ai_results.items():
            setattr(complaint, key, value)

        # Calculate trust score
        from .services import spam_service
        complaint.trust_score = spam_service.calculate_trust_score(complaint)
        complaint.save()

        return JsonResponse({
            'success': True,
            'complaint_code': complaint.complaint_code,
            'status': complaint.get_status_display(),
            'ai_verdict': complaint.ai_verdict,
            'category': complaint.get_category_display(),
            'message': _get_status_message(complaint.status)
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _get_status_message(status):
    """Get user-friendly message based on complaint status."""
    messages = {
        'published': 'Your complaint has been verified and published. It has been forwarded to the relevant government department.',
        'pending_review': 'Your complaint is being reviewed by our moderation team. You will be notified once it is processed.',
        'rejected': 'Your complaint could not be verified. Please submit with clearer evidence.',
    }
    return messages.get(status, 'Your complaint has been received.')


@require_http_methods(["GET"])
def api_complaint_status(request, code):
    """Track complaint by complaint_code."""
    try:
        complaint = Complaint.objects.get(complaint_code=code.upper())
        serializer = ComplaintDetailSerializer(complaint, context={'request': request})
        return JsonResponse(serializer.data)
    except Complaint.DoesNotExist:
        return JsonResponse({'error': 'Complaint not found'}, status=404)


@require_http_methods(["GET"])
def api_public_complaints(request):
    """Get all published complaints for public dashboard."""
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    sort = request.GET.get('sort', '-created_at')

    complaints = Complaint.objects.filter(status='published')

    if category and category != 'all':
        complaints = complaints.filter(category=category)
    if search:
        complaints = complaints.filter(
            Q(description__icontains=search) |
            Q(location_text__icontains=search) |
            Q(complaint_code__icontains=search)
        )

    # Sorting
    valid_sorts = ['-created_at', 'created_at', '-ai_severity_score', '-priority']
    if sort in valid_sorts:
        complaints = complaints.order_by(sort)

    serializer = ComplaintListSerializer(complaints, many=True, context={'request': request})
    return JsonResponse({'complaints': serializer.data, 'count': complaints.count()})


@require_http_methods(["GET"])
def api_dashboard_stats(request):
    """Public dashboard statistics."""
    total = Complaint.objects.count()
    published = Complaint.objects.filter(status='published').count()
    resolved = Complaint.objects.filter(status='resolved').count()
    pending = Complaint.objects.filter(status='pending_review').count()

    # Category breakdown
    category_stats = (
        Complaint.objects.filter(status__in=['published', 'resolved'])
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Recent 7 days trend
    week_ago = timezone.now() - timedelta(days=7)
    daily_counts = []
    for i in range(7):
        day = timezone.now() - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = Complaint.objects.filter(created_at__range=[day_start, day_end]).count()
        daily_counts.append({
            'date': day.strftime('%b %d'),
            'count': count
        })

    # Priority breakdown
    priority_stats = (
        Complaint.objects.filter(status__in=['published', 'pending_review'])
        .values('priority')
        .annotate(count=Count('id'))
    )

    return JsonResponse({
        'total': total,
        'published': published,
        'resolved': resolved,
        'pending': pending,
        'in_review': pending,
        'rejected': Complaint.objects.filter(status='rejected').count(),
        'category_stats': list(category_stats),
        'daily_trend': daily_counts,
        'priority_stats': list(priority_stats),
    })


@require_http_methods(["GET"])
def api_map_data(request):
    """Get complaint locations for map markers and heatmap."""
    complaints = Complaint.objects.filter(
        status__in=['published', 'resolved']
    ).values(
        'id', 'complaint_code', 'category', 'priority',
        'latitude', 'longitude', 'location_text',
        'description', 'status', 'ai_severity_score', 'created_at', 'ward'
    )

    # Convert to list with string dates
    data = []
    for c in complaints:
        c['created_at'] = c['created_at'].isoformat()
        data.append(c)

    # Include cluster data for hotspot overlays
    clusters = ComplaintCluster.objects.all().values(
        'cluster_id', 'complaint_count', 'severity_average',
        'center_latitude', 'center_longitude', 'radius_meters',
        'hotspot_priority_score', 'dominant_category', 'ward_name',
        'unresolved_count', 'category_breakdown'
    )

    return JsonResponse({
        'complaints': data,
        'clusters': list(clusters),
    })


# ============================================================
# MODERATION API
# ============================================================

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

        # Create moderation log
        ModerationLog.objects.create(
            complaint=complaint,
            moderator=request.user,
            action=action,
            notes=notes
        )

        # Update complaint status
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


# ============================================================
# GOVERNMENT API
# ============================================================

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


# ============================================================
# CONTACT FORM API
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_contact_submit(request):
    """Store a contact form message in the database."""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()

        if not name or not email or not message:
            return JsonResponse({'error': 'Name, email, and message are required'}, status=400)

        ContactMessage.objects.create(
            name=name, email=email, subject=subject, message=message
        )

        return JsonResponse({
            'success': True,
            'message': 'Thank you! Your message has been received. We will get back to you soon.'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# GOVERNMENT EXPORT / DOWNLOAD
# ============================================================

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

    # Apply filters from query params
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

    # Add metadata header
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


# ============================================================
# GEMINI AI IMAGE ANALYSIS
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_ai_analyze_image(request):
    """
    Analyze an uploaded image using Google Gemini API.
    Returns an auto-generated description of the civic issue.
    """
    import os
    import base64

    image_file = request.FILES.get('image')
    location = request.POST.get('location', '')

    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    # Read image bytes
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    mime_type = image_file.content_type or 'image/jpeg'

    # Check for Gemini API key
    api_key = os.environ.get('GEMINI_API_KEY', '')

    if not api_key:
        return JsonResponse({
            'success': False,
            'description': '',
            'message': 'Gemini API key not configured. Please add GEMINI_API_KEY to your .env file.',
        })

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build the prompt
        location_context = f" The location is: {location}." if location else ""

        prompt = f"""You are an AI assistant for AAWAJ, a civic complaint platform in Kathmandu Valley, Nepal.

Analyze this image and generate a clear, concise complaint description for a civic issue report.{location_context}

Rules:
- Describe what civic problem you see (pothole, garbage, water leak, broken infrastructure, etc.)
- Mention the severity (minor, moderate, severe)
- If location is provided, include it naturally in the description
- Keep it to 2-3 sentences maximum
- Write in English
- Be factual and descriptive, not emotional
- If the image does NOT show a civic issue, say "This image does not appear to show a civic issue."

Example output: "Large pothole approximately 2 feet wide on the main road near Ratnapark. The damage is severe and poses risk to vehicles and pedestrians. Immediate repair is recommended."

Generate the description now:"""

        # Send image to Gemini
        response = model.generate_content([
            prompt,
            {
                'mime_type': mime_type,
                'data': image_base64
            }
        ])

        description = response.text.strip()

        # Remove any markdown formatting Gemini might add
        description = description.replace('**', '').replace('*', '').strip('"').strip("'")

        return JsonResponse({
            'success': True,
            'description': description,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'description': '',
            'message': f'AI analysis failed: {str(e)}',
        })


# ============================================================
# PHASE 2 — ANALYTICS API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
def api_hotspots(request):
    """Get ranked hotspot clusters. Public endpoint."""
    from .services import hotspot_service

    limit = int(request.GET.get('limit', 10))
    hotspots = hotspot_service.get_top_hotspots(limit=limit)
    return JsonResponse({'hotspots': hotspots, 'count': len(hotspots)})


@require_http_methods(["GET"])
def api_priority_zones(request):
    """Get population-normalized priority zone rankings."""
    from .services import priority_engine

    zones = priority_engine.compute_ward_priority_scores()
    return JsonResponse({'zones': zones, 'count': len(zones)})


@require_http_methods(["GET"])
def api_analytics_heatmap(request):
    """Enhanced heatmap data with severity weighting and cluster overlays."""
    from .services import clustering_service

    complaints = Complaint.objects.filter(
        status__in=['published', 'resolved']
    ).values(
        'latitude', 'longitude', 'ai_severity_score', 'category', 'ward'
    )

    heatmap_points = [
        {
            'lat': c['latitude'],
            'lng': c['longitude'],
            'intensity': c['ai_severity_score'] / 10.0,
            'category': c['category'],
        }
        for c in complaints
    ]

    clusters_geojson = clustering_service.get_clusters_geojson()

    return JsonResponse({
        'heatmap': heatmap_points,
        'clusters': clusters_geojson,
    })


@require_http_methods(["GET"])
def api_analytics_trends(request):
    """Temporal trend data (daily/weekly/monthly)."""
    from .services import analytics_service

    days = int(request.GET.get('days', 30))
    granularity = request.GET.get('granularity', 'day')

    trends = analytics_service.get_temporal_trends(days=days, granularity=granularity)
    return JsonResponse({'trends': trends})


@require_http_methods(["GET"])
def api_analytics_ward_stats(request):
    """Per-ward complaint statistics."""
    from .services import geo_service

    stats = geo_service.get_ward_statistics()
    return JsonResponse({'wards': stats, 'count': len(stats)})


@require_http_methods(["GET"])
def api_analytics_severity(request):
    """Severity distribution and critical issue concentration."""
    from .services import analytics_service

    data = analytics_service.get_severity_distribution()
    return JsonResponse(data)


@require_http_methods(["GET"])
def api_clusters(request):
    """Raw cluster data for map visualization."""
    from .services import clustering_service

    geojson = clustering_service.get_clusters_geojson()
    return JsonResponse(geojson)


@require_http_methods(["GET"])
@role_required('government')
def api_government_performance(request):
    """Government response time and efficiency metrics."""
    from .services import analytics_service

    metrics = analytics_service.get_performance_metrics()
    return JsonResponse(metrics)


@require_http_methods(["GET"])
def api_analytics_duplicates(request):
    """Get duplicate complaint groups."""
    from .services import duplicate_service

    groups = duplicate_service.get_duplicate_groups()
    # Serialize dates
    for g in groups:
        for c in g['complaints']:
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()
    return JsonResponse({'groups': groups, 'count': len(groups)})


@csrf_exempt
@require_http_methods(["POST"])
@role_required('government')
def api_analytics_refresh(request):
    """Trigger re-computation of clusters/hotspots/duplicates."""
    from .services import clustering_service, hotspot_service, duplicate_service, spam_service, geo_service

    results = {}

    # Ward assignment
    unassigned = Complaint.objects.filter(ward='', status__in=['published', 'pending_review', 'resolved'])
    assigned = 0
    for c in unassigned:
        ward = geo_service.detect_ward(c.latitude, c.longitude)
        if ward:
            c.ward = ward
            c.save(update_fields=['ward'])
            assigned += 1
    results['wards_assigned'] = assigned

    # Clustering
    clusters = clustering_service.run_dbscan_clustering()
    saved = clustering_service.save_clusters(clusters)
    results['clusters_found'] = len(clusters)

    # Hotspot scoring
    hotspots = hotspot_service.compute_hotspot_scores()
    hotspot_service.save_hotspot_snapshot()
    results['hotspots_scored'] = len(hotspots)

    # Duplicates
    dup_count = duplicate_service.detect_duplicates()
    results['duplicates_found'] = dup_count

    # Trust scores
    updated = spam_service.update_all_trust_scores()
    results['trust_scores_updated'] = updated

    return JsonResponse({'success': True, 'results': results})
