"""
AAWAJ Shared View Helpers - Decorators used across multiple view modules.
"""

from functools import wraps
from django.http import JsonResponse


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
