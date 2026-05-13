"""
AAWAJ Analytics Service
Temporal analysis, performance metrics, and trend detection.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q

from ..models import Complaint, GovernmentAction


def get_temporal_trends(days=30, granularity='day'):
    """
    Get complaint counts over time.
    
    Args:
        days: Number of days to look back
        granularity: 'day', 'week', or 'month'
    
    Returns: list of {date, count, resolved, new}
    """
    now = timezone.now()
    cutoff = now - timedelta(days=days)
    
    results = []
    
    if granularity == 'day':
        for i in range(days):
            day = now - timedelta(days=days - 1 - i)
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            total = Complaint.objects.filter(created_at__range=[start, end]).count()
            resolved = Complaint.objects.filter(
                status='resolved', updated_at__range=[start, end]
            ).count()
            
            results.append({
                'date': day.strftime('%Y-%m-%d'),
                'label': day.strftime('%b %d'),
                'new_complaints': total,
                'resolved': resolved,
            })
    elif granularity == 'week':
        for i in range(days // 7):
            week_end = now - timedelta(weeks=i)
            week_start = week_end - timedelta(days=7)
            
            total = Complaint.objects.filter(
                created_at__range=[week_start, week_end]
            ).count()
            resolved = Complaint.objects.filter(
                status='resolved',
                updated_at__range=[week_start, week_end]
            ).count()
            
            results.append({
                'date': week_start.strftime('%Y-%m-%d'),
                'label': f"Week of {week_start.strftime('%b %d')}",
                'new_complaints': total,
                'resolved': resolved,
            })
        results.reverse()
    
    return results


def get_performance_metrics():
    """
    Calculate government response and resolution metrics.
    
    Returns: dict with performance stats
    """
    published = Complaint.objects.filter(status='published')
    resolved = Complaint.objects.filter(status='resolved')
    
    # Average resolution time
    resolution_times = []
    for c in resolved:
        last_action = c.government_actions.filter(action_type='resolved').first()
        if last_action:
            delta = (last_action.created_at - c.created_at).total_seconds() / 3600
            resolution_times.append(delta)
    
    avg_resolution_hours = (
        sum(resolution_times) / len(resolution_times)
        if resolution_times else 0
    )
    
    # Average response time (time to first government action)
    response_times = []
    for c in Complaint.objects.filter(
        status__in=['published', 'resolved']
    ).prefetch_related('government_actions'):
        first = c.government_actions.order_by('created_at').first()
        if first:
            delta = (first.created_at - c.created_at).total_seconds() / 3600
            response_times.append(delta)
    
    avg_response_hours = (
        sum(response_times) / len(response_times)
        if response_times else 0
    )
    
    # Department efficiency
    dept_stats = (
        GovernmentAction.objects
        .values('department')
        .annotate(action_count=Count('id'))
        .order_by('-action_count')
    )
    
    # Unresolved trend (last 7 days)
    now = timezone.now()
    unresolved_trend = []
    for i in range(7):
        day = now - timedelta(days=6 - i)
        count = Complaint.objects.filter(
            status='published',
            created_at__lte=day
        ).count()
        unresolved_trend.append({
            'date': day.strftime('%b %d'),
            'count': count,
        })
    
    total_complaints = Complaint.objects.filter(
        status__in=['published', 'resolved']
    ).count()
    total_resolved = resolved.count()
    
    return {
        'avg_resolution_hours': round(avg_resolution_hours, 1),
        'avg_resolution_days': round(avg_resolution_hours / 24, 1),
        'avg_response_hours': round(avg_response_hours, 1),
        'resolution_rate': round(
            (total_resolved / total_complaints * 100)
            if total_complaints > 0 else 0, 1
        ),
        'total_resolved': total_resolved,
        'total_active': published.count(),
        'department_stats': list(dept_stats),
        'unresolved_trend': unresolved_trend,
    }


def get_category_ward_breakdown():
    """
    Get category-wise complaint breakdown per ward.
    
    Returns: dict of {ward: {category: count, ...}, ...}
    """
    data = (
        Complaint.objects
        .filter(status__in=['published', 'resolved'], ward__gt='')
        .values('ward', 'category')
        .annotate(count=Count('id'))
        .order_by('ward', '-count')
    )
    
    breakdown = {}
    for row in data:
        ward = row['ward']
        if ward not in breakdown:
            breakdown[ward] = {}
        breakdown[ward][row['category']] = row['count']
    
    return breakdown


def get_severity_distribution():
    """
    Get severity score distribution and critical issue concentration.
    
    Returns: dict with severity data
    """
    complaints = Complaint.objects.filter(status__in=['published', 'pending_review'])
    
    # Severity histogram
    histogram = {}
    for i in range(1, 11):
        histogram[str(i)] = complaints.filter(ai_severity_score=i).count()
    
    # Critical concentration by ward
    critical = (
        complaints.filter(ai_severity_score__gte=8)
        .values('ward')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    
    # Category severity averages
    category_severity = (
        complaints.values('category')
        .annotate(avg_severity=Avg('ai_severity_score'), count=Count('id'))
        .order_by('-avg_severity')
    )
    
    return {
        'histogram': histogram,
        'critical_zones': list(critical),
        'category_severity': list(category_severity),
        'total_critical': complaints.filter(ai_severity_score__gte=8).count(),
        'total_high': complaints.filter(ai_severity_score__gte=6, ai_severity_score__lt=8).count(),
        'total_moderate': complaints.filter(ai_severity_score__gte=4, ai_severity_score__lt=6).count(),
        'total_low': complaints.filter(ai_severity_score__lt=4).count(),
    }
