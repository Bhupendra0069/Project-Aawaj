"""
Custom context processors for AAWAJ templates.
"""


def user_role(request):
    """Add user role flags to template context."""
    if request.user.is_authenticated:
        return {
            'is_moderator': request.user.groups.filter(name='moderator').exists() or request.user.is_superuser,
            'is_government': request.user.groups.filter(name='government').exists() or request.user.is_superuser,
        }
    return {
        'is_moderator': False,
        'is_government': False,
    }





