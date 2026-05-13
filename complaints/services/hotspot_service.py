"""
AAWAJ Hotspot Service
Combines clustering results with priority scoring for hotspot ranking.
"""

from django.utils import timezone
from datetime import timedelta

from ..models import ComplaintCluster, HotspotAnalytics, RegionPopulation, AnalyticsConfig
from . import clustering_service, priority_engine


def compute_hotspot_scores():
    """
    Compute priority scores for all clusters using the priority engine formula.
    Updates the hotspot_priority_score on each ComplaintCluster.

    Returns: list of clusters sorted by priority score
    """
    config = AnalyticsConfig.get_config()
    clusters = ComplaintCluster.objects.all()
    ward_scores = {
        w['ward_name']: w
        for w in priority_engine.compute_ward_priority_scores()
    }

    results = []
    for cluster in clusters:
        ward_data = ward_scores.get(cluster.ward_name, {})
        ward_priority = ward_data.get('priority_score', 0)

        severity_factor = (cluster.severity_average / 10.0) * config.severity_weight
        count_factor = cluster.complaint_count
        unresolved_ratio = (
            cluster.unresolved_count / cluster.complaint_count
            if cluster.complaint_count > 0 else 0
        )
        density_factor = min(cluster.density_score / 100, 5.0)

        try:
            region = RegionPopulation.objects.get(ward_name=cluster.ward_name)
            pop_density = region.population_density if region.population_density > 0 else 1
        except RegionPopulation.DoesNotExist:
            pop_density = 1

        score = (
            count_factor *
            severity_factor *
            (1.0 + unresolved_ratio) *
            (1.0 + density_factor * 0.1)
        ) / (pop_density / 1000)

        blended_score = score * 0.7 + ward_priority * 0.3

        cluster.hotspot_priority_score = round(blended_score, 2)
        cluster.save()

        results.append({
            'cluster_id': cluster.cluster_id,
            'ward_name': cluster.ward_name,
            'priority_score': cluster.hotspot_priority_score,
            'complaint_count': cluster.complaint_count,
            'severity_average': cluster.severity_average,
            'unresolved_count': cluster.unresolved_count,
            'center_lat': cluster.center_latitude,
            'center_lng': cluster.center_longitude,
            'radius_meters': cluster.radius_meters,
            'dominant_category': cluster.dominant_category,
            'category_breakdown': cluster.category_breakdown,
        })

    results.sort(key=lambda x: x['priority_score'], reverse=True)
    return results


def save_hotspot_snapshot():
    """
    Save a snapshot of current hotspot state for trend tracking.

    Returns: number of snapshots saved
    """
    clusters = ComplaintCluster.objects.all()
    count = 0

    for cluster in clusters:
        HotspotAnalytics.objects.create(
            cluster=cluster,
            ward_name=cluster.ward_name,
            complaint_count=cluster.complaint_count,
            severity_average=cluster.severity_average,
            priority_score=cluster.hotspot_priority_score,
            unresolved_count=cluster.unresolved_count,
        )
        count += 1

    return count


def get_top_hotspots(limit=10):
    """Get the top-N hotspot clusters by priority score."""
    clusters = ComplaintCluster.objects.order_by(
        '-hotspot_priority_score'
    )[:limit]
    return [
        {
            'cluster_id': c.cluster_id,
            'ward_name': c.ward_name,
            'priority_score': c.hotspot_priority_score,
            'complaint_count': c.complaint_count,
            'severity_average': c.severity_average,
            'unresolved_count': c.unresolved_count,
            'center_lat': c.center_latitude,
            'center_lng': c.center_longitude,
            'radius_meters': c.radius_meters,
            'dominant_category': c.dominant_category,
            'category_breakdown': c.category_breakdown,
        }
        for c in clusters
    ]


def get_hotspot_trends(ward_name=None, days=30):
    """Get hotspot trend data over time."""
    cutoff = timezone.now().date() - timedelta(days=days)
    qs = HotspotAnalytics.objects.filter(snapshot_date__gte=cutoff)

    if ward_name:
        qs = qs.filter(ward_name=ward_name)

    qs = qs.order_by('snapshot_date')

    return list(qs.values(
        'snapshot_date', 'ward_name', 'complaint_count',
        'severity_average', 'priority_score', 'unresolved_count'
    ))
