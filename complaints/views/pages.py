"""
AAWAJ Page Views - Template rendering views.
Handles all HTML page routes (home, login, report, dashboards, etc.)
"""

from functools import wraps

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


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
# PUBLIC PAGES
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


# ============================================================
# AUTH PAGES
# ============================================================

def login_view(request):
    """Login page for moderators/government/admin."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        selected_role = request.POST.get('role', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Validate selected role matches user's group
            if selected_role == 'moderator':
                if not user.groups.filter(name='moderator').exists() and not user.is_superuser:
                    return JsonResponse({'success': False, 'error': 'This account does not have moderator access'}, status=403)
                login(request, user)
                return JsonResponse({'success': True, 'redirect': '/moderation/'})
            elif selected_role == 'government':
                if not user.groups.filter(name='government').exists() and not user.is_superuser:
                    return JsonResponse({'success': False, 'error': 'This account does not have government access'}, status=403)
                login(request, user)
                return JsonResponse({'success': True, 'redirect': '/government/'})
            else:
                # Fallback: redirect based on user group
                login(request, user)
                if user.groups.filter(name='government').exists():
                    return JsonResponse({'success': True, 'redirect': '/government/'})
                elif user.groups.filter(name='moderator').exists():
                    return JsonResponse({'success': True, 'redirect': '/moderation/'})
                else:
                    return JsonResponse({'success': True, 'redirect': '/moderation/'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid username or password'}, status=401)
    return render(request, 'login.html')

def logout_view(request):
    """Logout and redirect to home."""
    logout(request)
    return redirect('/')


# ============================================================
# PROTECTED PAGES (Role-Based)
# ============================================================

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
# PUBLIC PAGES (Resolved Cases)
# ============================================================

def resolved_cases_view(request):
    """Resolved cases public page — shows all resolved complaints with resolution details."""
    return render(request, 'resolved_cases.html')
