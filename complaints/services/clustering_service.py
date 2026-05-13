"""
AAWAJ Clustering Service
DBSCAN-based geospatial complaint clustering for hotspot detection.
"""

import math
import numpy as np
from collections import Counter
from sklearn.cluster import DBSCAN

from django.utils import timezone

from ..models import Complaint, ComplaintCluster, AnalyticsConfig
from . import geo_service


def _meters_to_radians(meters):
    """Convert meters to radians for haversine-based DBSCAN."""
    return meters / 6371000.0


def run_dbscan_clustering(category=None, status_filter=None):
    """
    Run DBSCAN clustering on complaint coordinates.

    Args:
        category: Optional category filter (e.g., 'roads')
        status_filter: Optional list of statuses (defaults to published + pending_review)

    Returns: list of cluster dicts with metadata
    """
    config = AnalyticsConfig.get_config()

    if status_filter is None:
        status_filter = ['published', 'pending_review']

    complaints = Complaint.objects.filter(status__in=status_filter)
    if category:
        complaints = complaints.filter(category=category)

    complaints = complaints.values(
        'id', 'latitude', 'longitude', 'category', 'priority',
        'ai_severity_score', 'ai_urgency', 'status', 'ward',
        'complaint_code', 'created_at', 'trust_score'
    )

    complaint_list = list(complaints)
    if len(complaint_list) < config.dbscan_min_samples:
        return []

    # Prepare coordinate matrix
    coords = np.array([
        [math.radians(c['latitude']), math.radians(c['longitude'])]
        for c in complaint_list
    ])

    # Run DBSCAN with haversine metric
    eps_radians = _meters_to_radians(config.dbscan_eps_meters)
    db = DBSCAN(
        eps=eps_radians,
        min_samples=config.dbscan_min_samples,
        metric='haversine'
    )
    labels = db.fit_predict(coords)

    # Group complaints by cluster label
    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue  # Skip noise
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(complaint_list[idx])

    # Build cluster metadata
    results = []
    for cluster_id, members in clusters.items():
        lats = [m['latitude'] for m in members]
        lngs = [m['longitude'] for m in members]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)

        # Calculate cluster radius (max distance from center)
        max_dist = max(
            geo_service.haversine_distance(center_lat, center_lng, m['latitude'], m['longitude'])
            for m in members
        )

        # Category breakdown
        categories = Counter(m['category'] for m in members)
        dominant = categories.most_common(1)[0][0] if categories else ''

        # Severity stats
        severities = [m['ai_severity_score'] for m in members]
        avg_severity = sum(severities) / len(severities)
        urgent_count = sum(1 for m in members if m['ai_urgency'])
        unresolved = sum(1 for m in members if m['status'] != 'resolved')

        # Density score: complaints per 1000 sq meters of cluster area
        area_m2 = math.pi * (max_dist ** 2) if max_dist > 0 else 1
        density = (len(members) / area_m2) * 1000000  # per km²

        # Ward detection for cluster center
        ward = geo_service.detect_ward(center_lat, center_lng)

        results.append({
            'cluster_id': int(cluster_id),
            'complaint_count': len(members),
            'severity_average': round(avg_severity, 2),
            'density_score': round(density, 2),
            'center_latitude': round(center_lat, 6),
            'center_longitude': round(center_lng, 6),
            'radius_meters': round(max_dist, 1),
            'dominant_category': dominant,
            'category_breakdown': dict(categories),
            'ward_name': ward,
            'unresolved_count': unresolved,
            'urgent_count': urgent_count,
            'complaint_ids': [m['id'] for m in members],
        })

    # Sort by complaint count descending
    results.sort(key=lambda x: x['complaint_count'], reverse=True)

    return results


def save_clusters(cluster_results):
    """
    Save DBSCAN cluster results to the ComplaintCluster model.
    Clears old clusters and creates new ones.

    Args:
        cluster_results: list of cluster dicts from run_dbscan_clustering()

    Returns: number of clusters saved
    """
    # Clear old clusters
    ComplaintCluster.objects.all().delete()

    created = []
    for c in cluster_results:
        obj = ComplaintCluster.objects.create(
            cluster_id=c['cluster_id'],
            complaint_count=c['complaint_count'],
            severity_average=c['severity_average'],
            density_score=c['density_score'],
            center_latitude=c['center_latitude'],
            center_longitude=c['center_longitude'],
            radius_meters=c['radius_meters'],
            dominant_category=c['dominant_category'],
            category_breakdown=c['category_breakdown'],
            ward_name=c['ward_name'],
            unresolved_count=c['unresolved_count'],
        )
        created.append(obj)

    return len(created)


def get_clusters_geojson():
    """
    Get all clusters as GeoJSON for map visualization.

    Returns: GeoJSON FeatureCollection dict
    """
    clusters = ComplaintCluster.objects.all()
    features = []

    for c in clusters:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [c.center_longitude, c.center_latitude]
            },
            'properties': {
                'cluster_id': c.cluster_id,
                'complaint_count': c.complaint_count,
                'severity_average': c.severity_average,
                'density_score': c.density_score,
                'radius_meters': c.radius_meters,
                'dominant_category': c.dominant_category,
                'category_breakdown': c.category_breakdown,
                'ward_name': c.ward_name,
                'unresolved_count': c.unresolved_count,
                'priority_score': c.hotspot_priority_score,
            }
        })

    return {
        'type': 'FeatureCollection',
        'features': features
    }
