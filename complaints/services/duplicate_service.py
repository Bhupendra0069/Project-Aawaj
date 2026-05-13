"""
AAWAJ Duplicate Complaint Detection Service
Detects similar/duplicate complaints using GPS proximity, text similarity, and time windows.
"""

from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Q

from ..models import Complaint, ComplaintSimilarity, AnalyticsConfig
from . import geo_service


def _compute_text_similarity(text_a, text_b):
    """
    Compute cosine similarity between two texts using TF-IDF.
    Falls back to simple Jaccard similarity if sklearn fails.
    """
    if not text_a or not text_b:
        return 0.0

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
        tfidf = vectorizer.fit_transform([text_a, text_b])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return float(sim)
    except Exception:
        # Fallback: Jaccard similarity
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)


def detect_duplicates(complaint=None):
    """
    Detect duplicate/similar complaints.
    If a specific complaint is given, finds its duplicates.
    Otherwise, scans all recent complaints.

    Returns: number of similarity records created
    """
    config = AnalyticsConfig.get_config()
    created_count = 0

    if complaint:
        complaints_to_check = [complaint]
    else:
        # Check complaints from the last N days
        cutoff = timezone.now() - timedelta(days=config.duplicate_time_days * 2)
        complaints_to_check = Complaint.objects.filter(
            created_at__gte=cutoff,
            status__in=['published', 'pending_review', 'pending_ai']
        )

    for comp in complaints_to_check:
        # Find candidates: same category, within time window, within radius
        time_cutoff = comp.created_at - timedelta(days=config.duplicate_time_days)
        time_end = comp.created_at + timedelta(days=config.duplicate_time_days)

        candidates = Complaint.objects.filter(
            category=comp.category,
            created_at__range=[time_cutoff, time_end],
            status__in=['published', 'pending_review']
        ).exclude(id=comp.id)

        for candidate in candidates:
            # Skip if already compared
            exists = ComplaintSimilarity.objects.filter(
                Q(complaint_a=comp, complaint_b=candidate) |
                Q(complaint_a=candidate, complaint_b=comp)
            ).exists()
            if exists:
                continue

            # GPS distance
            gps_dist = geo_service.haversine_distance(
                comp.latitude, comp.longitude,
                candidate.latitude, candidate.longitude
            )

            # Only compare if within a reasonable radius (5x duplicate radius)
            if gps_dist > config.duplicate_radius_meters * 5:
                continue

            # Text similarity
            text_sim = _compute_text_similarity(
                comp.description, candidate.description
            )

            # GPS proximity score (1.0 at 0m, 0.0 at duplicate_radius * 2)
            gps_score = max(0, 1.0 - gps_dist / (config.duplicate_radius_meters * 2))

            # Combined similarity score
            combined = (gps_score * 0.5 + text_sim * 0.5)

            # Determine if it's a duplicate
            is_dup = (
                gps_dist <= config.duplicate_radius_meters and
                (text_sim >= config.duplicate_text_threshold or gps_score >= 0.8)
            )

            if combined >= 0.3:  # Only store meaningful similarities
                ComplaintSimilarity.objects.create(
                    complaint_a=comp,
                    complaint_b=candidate,
                    similarity_score=round(combined, 3),
                    method='combined',
                    gps_distance_meters=round(gps_dist, 1),
                    text_similarity=round(text_sim, 3),
                    is_duplicate=is_dup,
                )
                created_count += 1

    return created_count


def get_duplicate_groups():
    """
    Get groups of duplicate complaints.

    Returns: list of groups, each containing related complaint codes
    """
    duplicates = ComplaintSimilarity.objects.filter(is_duplicate=True)

    # Build adjacency groups using union-find
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for dup in duplicates:
        union(dup.complaint_a_id, dup.complaint_b_id)

    # Group by root
    groups = defaultdict(set)
    all_ids = set()
    for dup in duplicates:
        all_ids.add(dup.complaint_a_id)
        all_ids.add(dup.complaint_b_id)

    for cid in all_ids:
        groups[find(cid)].add(cid)

    # Fetch complaint details
    result = []
    for root, member_ids in groups.items():
        complaints = Complaint.objects.filter(id__in=member_ids).values(
            'id', 'complaint_code', 'category', 'location_text',
            'latitude', 'longitude', 'ai_severity_score', 'created_at'
        )
        result.append({
            'group_size': len(member_ids),
            'complaints': list(complaints),
        })

    result.sort(key=lambda x: x['group_size'], reverse=True)
    return result
