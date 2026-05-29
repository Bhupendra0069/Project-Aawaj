"""
AAWAJ Complaints API - Public complaint endpoints.
Handles complaint submission, tracking, public dashboard, map data, and AI image analysis.
"""

import json

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from ..models import (
    Complaint, ComplaintImage, ComplaintAudio,
    ContactMessage, ComplaintCluster
)
from ..serializers import ComplaintListSerializer, ComplaintDetailSerializer
from .. import ai_service


# ============================================================
# COMPLAINT SUBMISSION
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
        category = request.POST.get('category', 'other')

        images = request.FILES.getlist('images')
        audio = request.FILES.get('audio')

        # Validation
        if not location_text:
            return JsonResponse({'error': 'Location is required'}, status=400)
        if not images:
            return JsonResponse({'error': 'At least one image is required'}, status=400)
        if not description and not audio:
            return JsonResponse({'error': 'Either text description or audio is required'}, status=400)

        # ===== CHECK FOR DUPLICATE IMAGES =====
        from ..image_utils import check_duplicate_by_location
        
        # Check all images for duplicates
        for i, image in enumerate(images):
            duplicate_check = check_duplicate_by_location(
                image,
                latitude,
                longitude,
                category,
                radius_meters=500  # 500m radius = same location
            )
            
            if duplicate_check['is_duplicate']:
                return JsonResponse({
                    'error': 'Duplicate complaint',
                    'message': duplicate_check['message'],
                    'original_complaint': duplicate_check['duplicate_complaint'].complaint_code,
                    'original_location': duplicate_check['duplicate_location'],
                    'distance_meters': duplicate_check.get('distance_meters', 0)
                }, status=409)  # 409 = Conflict
        # ===== END: DUPLICATE CHECK =====

        # Auto-detect ward from coordinates
        from ..services import geo_service
        ward = geo_service.detect_ward(latitude, longitude)

        # Create complaint
        complaint = Complaint.objects.create(
            description=description,
            location_text=location_text,
            latitude=latitude,
            longitude=longitude,
            ward=ward,
            status='pending_ai',
            category=category
        )

        # Save images WITH HASH
        from ..image_utils import calculate_image_hash
        for img in images:
            image_hash = calculate_image_hash(img)
            ComplaintImage.objects.create(
                complaint=complaint, 
                image=img,
                image_hash=image_hash
            )

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

        # Fields returned by AI that are NOT model columns — skip them in setattr
        non_model_fields = {'description_match_score', 'image_description', 'detected_issues'}

        # Update complaint with AI results (only model fields)
        for key, value in ai_results.items():
            if key not in non_model_fields:
                setattr(complaint, key, value)

        # Calculate trust score
        from ..services import spam_service
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


# ============================================================
# DUPLICATE CHECK
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_check_duplicate_image(request):
    """Check if uploaded image is duplicate (different location)."""
    try:
        image = request.FILES.get('image')
        latitude = float(request.POST.get('latitude', 27.7172))
        longitude = float(request.POST.get('longitude', 85.3240))
        category = request.POST.get('category', 'other')
        
        if not image:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        from ..image_utils import check_duplicate_by_location
        
        result = check_duplicate_by_location(
            image, latitude, longitude, category
        )
        
        return JsonResponse({
            'is_duplicate': result['is_duplicate'],
            'message': result['message'],
            'duplicate_location': result['duplicate_location'],
            'distance': result.get('distance_meters', 0),
            'original_complaint': result['duplicate_complaint'].complaint_code if result['duplicate_complaint'] else None
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# COMPLAINT TRACKING & PUBLIC DATA
# ============================================================

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
# AI IMAGE ANALYSIS (Groq Vision)
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_ai_analyze_image(request):
    """
    Analyze an uploaded image using Groq Vision API (Llama 4 Scout).
    Returns an auto-generated description of the civic issue.
    """
    import os
    import base64
    import requests as http_requests

    image_file = request.FILES.get('image')
    location = request.POST.get('location', '')

    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    # Read image bytes
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    mime_type = image_file.content_type or 'image/jpeg'

    # Check for Groq API key
    api_key = os.environ.get('GROQ_API_KEY', '')

    if not api_key:
        return JsonResponse({
            'success': False,
            'description': '',
            'message': 'Groq API key not configured. Please add GROQ_API_KEY to your .env file.',
        })

    try:
        # Build the prompt — with strict screenshot/fake image detection
        location_context = f" The location is: {location}." if location else ""

        prompt = f"""You are an AI assistant for AAWAJ, a civic complaint platform in Kathmandu Valley, Nepal.

Analyze this image and generate a clear, concise complaint description for a civic issue report.{location_context}

FIRST, determine if this is a REAL PHOTOGRAPH of a physical location/issue:
- If this is a SCREENSHOT of a website, app, form, or computer screen, respond with EXACTLY: "This image is a screenshot, not a real photo of a civic issue. Please upload an actual photograph of the problem."
- If this is NOT a photo of a civic issue (selfie, food, indoor, etc.), respond with EXACTLY: "This image does not appear to show a civic issue. Please upload a photo showing the actual problem."

ONLY if it IS a real photo of a civic issue, then:
- Describe what civic problem you see (pothole, garbage, water leak, broken infrastructure, etc.)
- Mention the severity (minor, moderate, severe)
- If location is provided, include it naturally in the description
- Keep it to 2-3 sentences maximum
- Write in English
- Be factual and descriptive, not emotional

Example output: "Large pothole approximately 2 feet wide on the main road near Ratnapark. The damage is severe and poses risk to vehicles and pedestrians. Immediate repair is recommended."

Generate the description now:"""

        # Call Groq Vision API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        response = http_requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        description = data["choices"][0]["message"]["content"].strip()

        # Remove any markdown formatting
        description = description.replace('**', '').replace('*', '').strip('"').strip("'")

        # Check if AI flagged this as not a civic issue
        is_civic = True
        lower_desc = description.lower()
        if 'screenshot' in lower_desc or 'not a real photo' in lower_desc or 'does not appear to show a civic issue' in lower_desc:
            is_civic = False

        return JsonResponse({
            'success': True,
            'description': description,
            'is_civic_issue': is_civic,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'description': '',
            'message': f'AI analysis failed: {str(e)}',
        })


# ============================================================
# CONTACT FORM
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
