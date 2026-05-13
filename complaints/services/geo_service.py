"""
AAWAJ Geospatial Service
Utility functions for geographic calculations, ward detection, and GeoJSON generation.
"""

import math
from ..models import RegionPopulation


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    Returns: distance in meters
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def detect_ward(latitude, longitude):
    """
    Detect the nearest ward based on GPS coordinates.
    Finds the RegionPopulation record whose center is closest.

    Returns: ward_name (str) or '' if no wards exist
    """
    wards = RegionPopulation.objects.all()
    if not wards.exists():
        return ''

    closest_ward = None
    min_distance = float('inf')

    for ward in wards:
        dist = haversine_distance(
            latitude, longitude,
            ward.center_latitude, ward.center_longitude
        )
        if dist < min_distance:
            min_distance = dist
            closest_ward = ward

    return closest_ward.ward_name if closest_ward else ''


def get_complaints_in_radius(latitude, longitude, radius_meters, queryset=None):
    """
    Get all complaints within a given radius of a point.
    Uses a bounding box pre-filter for efficiency, then refines with haversine.

    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_meters: Radius in meters
        queryset: Optional pre-filtered queryset (defaults to all published)

    Returns: list of complaint objects within radius
    """
    from ..models import Complaint

    if queryset is None:
        queryset = Complaint.objects.filter(status__in=['published', 'resolved'])

    # Approximate bounding box (1 degree ≈ 111km)
    delta_lat = radius_meters / 111000.0
    delta_lon = radius_meters / (111000.0 * math.cos(math.radians(latitude)))

    # Pre-filter with bounding box (fast DB query)
    candidates = queryset.filter(
        latitude__gte=latitude - delta_lat,
        latitude__lte=latitude + delta_lat,
        longitude__gte=longitude - delta_lon,
        longitude__lte=longitude + delta_lon,
    )

    # Refine with actual haversine distance
    results = []
    for c in candidates:
        dist = haversine_distance(latitude, longitude, c.latitude, c.longitude)
        if dist <= radius_meters:
            results.append((c, dist))

    return results


def generate_geojson(complaints):
    """
    Convert a list of complaint dicts/objects to GeoJSON FeatureCollection.

    Args:
        complaints: queryset or list of complaint-like objects with latitude/longitude

    Returns: GeoJSON dict
    """
    features = []
    for c in complaints:
        lat = getattr(c, 'latitude', None) or c.get('latitude')
        lng = getattr(c, 'longitude', None) or c.get('longitude')

        if lat is None or lng is None:
            continue

        properties = {}
        for field in ['complaint_code', 'category', 'priority', 'status',
                       'ai_severity_score', 'location_text', 'description']:
            val = getattr(c, field, None)
            if val is None and isinstance(c, dict):
                val = c.get(field)
            properties[field] = val

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(lng), float(lat)]
            },
            'properties': properties
        })

    return {
        'type': 'FeatureCollection',
        'features': features
    }


def get_ward_statistics():
    """
    Get complaint statistics per ward.

    Returns: list of dicts with ward info and complaint counts
    """
    from ..models import Complaint
    from django.db.models import Count, Avg, Q

    wards = RegionPopulation.objects.all()
    stats = []

    for ward in wards:
        ward_complaints = Complaint.objects.filter(
            ward=ward.ward_name,
            status__in=['published', 'resolved']
        )

        total = ward_complaints.count()
        unresolved = ward_complaints.filter(status='published').count()
        resolved = ward_complaints.filter(status='resolved').count()
        avg_severity = ward_complaints.aggregate(
            avg=Avg('ai_severity_score')
        )['avg'] or 0

        # Complaint rate per 1000 population
        rate = (total / ward.population * 1000) if ward.population > 0 else 0

        stats.append({
            'ward_name': ward.ward_name,
            'ward_number': ward.ward_number,
            'municipality': ward.municipality,
            'population': ward.population,
            'area_km2': ward.area_km2,
            'population_density': ward.population_density,
            'total_complaints': total,
            'unresolved': unresolved,
            'resolved': resolved,
            'avg_severity': round(avg_severity, 1),
            'complaint_rate_per_1k': round(rate, 2),
            'center_lat': ward.center_latitude,
            'center_lng': ward.center_longitude,
        })

    return sorted(stats, key=lambda x: x['complaint_rate_per_1k'], reverse=True)
