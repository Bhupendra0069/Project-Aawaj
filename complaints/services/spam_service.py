"""
AAWAJ Spam / Fake Detection Service
Detects spam, suspicious patterns, and calculates complaint trust scores.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from ..models import Complaint, AnalyticsConfig


def calculate_trust_score(complaint):
    """
    Calculate a trust score (0.0 - 1.0) for a complaint.
    Considers: AI confidence, image genuineness, submission patterns, text quality.

    Returns: float trust score
    """
    score = 1.0

    # Factor 1: AI confidence (0.6-1.0 = good)
    if complaint.ai_confidence_score < 0.4:
        score -= 0.3
    elif complaint.ai_confidence_score < 0.6:
        score -= 0.1

    # Factor 2: AI fake detection
    if complaint.ai_is_fake:
        score -= 0.4

    # Factor 3: Description quality
    desc = complaint.description or ''
    if len(desc) < 10:
        score -= 0.15
    elif len(desc) < 30:
        score -= 0.05

    # Factor 4: Location validity (rough check for Kathmandu Valley)
    lat, lng = complaint.latitude, complaint.longitude
    if not (27.5 <= lat <= 27.9 and 85.1 <= lng <= 85.6):
        score -= 0.3  # Outside Kathmandu Valley

    # Factor 5: Suspicious frequency (same location, last 24h)
    config = AnalyticsConfig.get_config()
    recent_same_location = Complaint.objects.filter(
        latitude__range=(lat - 0.001, lat + 0.001),
        longitude__range=(lng - 0.001, lng + 0.001),
        created_at__gte=timezone.now() - timedelta(hours=24),
    ).exclude(id=complaint.id).count()

    if recent_same_location >= config.spam_frequency_limit:
        score -= 0.3
    elif recent_same_location >= config.spam_frequency_limit // 2:
        score -= 0.1

    return max(0.0, min(1.0, round(score, 2)))


def detect_spam_complaints():
    """
    Scan recent complaints for spam patterns.

    Returns: list of complaint IDs flagged as suspicious
    """
    config = AnalyticsConfig.get_config()
    cutoff = timezone.now() - timedelta(hours=24)

    # Find location clusters with too many submissions

    
    suspicious = []
    recent = Complaint.objects.filter(created_at__gte=cutoff)

    for complaint in recent:
        trust = calculate_trust_score(complaint)
        if trust < 0.5:
            suspicious.append({
                'id': complaint.id,
                'complaint_code': complaint.complaint_code,
                'trust_score': trust,
                'reason': 'Low trust score',
            })
            # Update trust score in DB
            complaint.trust_score = trust
            complaint.save(update_fields=['trust_score'])

    return suspicious


def update_all_trust_scores():
    """
    Recalculate trust scores for all non-resolved complaints.

    Returns: number of complaints updated
    """
    complaints = Complaint.objects.filter(
        status__in=['published', 'pending_review', 'pending_ai']
    )
    count = 0
    for c in complaints:
        new_score = calculate_trust_score(c)
        if abs(c.trust_score - new_score) > 0.01:
            c.trust_score = new_score
            c.save(update_fields=['trust_score'])
            count += 1
    return count
