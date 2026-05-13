"""
AAWAJ Priority Engine
Population-normalized complaint prioritization.

Formula:
    PriorityScore = (ComplaintCount × SeverityWeight × UrgencyWeight ×
                     RecurringFactor × VerificationScore × RecencyFactor)
                    / PopulationDensity
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q

from ..models import Complaint, RegionPopulation, AnalyticsConfig, ComplaintSimilarity


def _get_recency_factor(complaints):
    """
    Calculate recency factor: recent unresolved complaints increase the score.
    Complaints in the last 7 days get 2x, last 30 days get 1.5x, older get 1x.
    """
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    recent_7d = complaints.filter(created_at__gte=week_ago).count()
    recent_30d = complaints.filter(
        created_at__gte=month_ago, created_at__lt=week_ago
    ).count()
    older = complaints.filter(created_at__lt=month_ago).count()

    total = recent_7d + recent_30d + older
    if total == 0:
        return 1.0

    weighted = (recent_7d * 2.0 + recent_30d * 1.5 + older * 1.0) / total
    return weighted


def _get_recurring_factor(ward_name, config):
    """
    Calculate recurring factor based on duplicate complaints in the ward.
    More duplicates = higher recurring factor.
    """
    ward_complaints = Complaint.objects.filter(
        ward=ward_name, status__in=['published', 'resolved']
    ).values_list('id', flat=True)

    duplicate_count = ComplaintSimilarity.objects.filter(
        complaint_a__id__in=ward_complaints,
        is_duplicate=True
    ).count()

    if duplicate_count == 0:
        return 1.0

    # Logarithmic scaling so it doesn't grow unboundedly
    import math
    return 1.0 + math.log1p(duplicate_count) * 0.3


def _get_verification_score(complaints):
    """
    Average trust/verification score for complaints.
    Higher confidence + non-fake = better verification.
    """
    verified = complaints.filter(ai_is_fake=False, ai_confidence_score__gte=0.6)
    total = complaints.count()

    if total == 0:
        return 1.0

    return (verified.count() / total) * 1.0 + 0.5


def compute_ward_priority_scores():
    """
    Compute population-normalized priority scores for all wards.

    Returns: list of dicts sorted by priority_score descending
        [{'ward_name': '...', 'priority_score': float, 'details': {...}}, ...]
    """
    config = AnalyticsConfig.get_config()
    wards = RegionPopulation.objects.all()
    results = []

    for ward in wards:
        complaints = Complaint.objects.filter(
            ward=ward.ward_name,
            status__in=['published', 'pending_review']
        )

        complaint_count = complaints.count()
        if complaint_count == 0:
            results.append({
                'ward_name': ward.ward_name,
                'ward_number': ward.ward_number,
                'municipality': ward.municipality,
                'priority_score': 0.0,
                'complaint_count': 0,
                'population': ward.population,
                'population_density': ward.population_density,
                'details': {},
            })
            continue

        # Component scores
        avg_severity = complaints.aggregate(avg=Avg('ai_severity_score'))['avg'] or 5
        urgency_count = complaints.filter(ai_urgency=True).count()
        urgency_ratio = urgency_count / complaint_count if complaint_count > 0 else 0
        critical_count = complaints.filter(priority='critical').count()
        high_count = complaints.filter(priority='high').count()
        unresolved = complaints.filter(status='published').count()

        severity_component = (avg_severity / 10.0) * config.severity_weight
        urgency_component = (1.0 + urgency_ratio * config.urgency_weight)
        recency_factor = _get_recency_factor(complaints) * config.recency_weight
        verification_score = _get_verification_score(complaints) * config.verification_weight
        recurring_factor = _get_recurring_factor(ward.ward_name, config) * config.recurring_weight

        # Population normalization
        pop_density = ward.population_density if ward.population_density > 0 else 1.0
        pop_normalizer = pop_density ** config.population_weight

        # Final score
        raw_score = (
            complaint_count *
            severity_component *
            urgency_component *
            recurring_factor *
            verification_score *
            recency_factor
        )

        # Normalize by population density
        priority_score = raw_score / (pop_normalizer / 1000)  # scale factor

        results.append({
            'ward_name': ward.ward_name,
            'ward_number': ward.ward_number,
            'municipality': ward.municipality,
            'priority_score': round(priority_score, 2),
            'complaint_count': complaint_count,
            'unresolved': unresolved,
            'population': ward.population,
            'population_density': round(ward.population_density, 1),
            'avg_severity': round(avg_severity, 1),
            'critical_count': critical_count,
            'high_count': high_count,
            'urgency_count': urgency_count,
            'center_lat': ward.center_latitude,
            'center_lng': ward.center_longitude,
            'details': {
                'severity_component': round(severity_component, 3),
                'urgency_component': round(urgency_component, 3),
                'recency_factor': round(recency_factor, 3),
                'verification_score': round(verification_score, 3),
                'recurring_factor': round(recurring_factor, 3),
                'pop_normalizer': round(pop_normalizer, 3),
            }
        })

    # Sort by priority score descending
    results.sort(key=lambda x: x['priority_score'], reverse=True)

    # Add rank
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results
