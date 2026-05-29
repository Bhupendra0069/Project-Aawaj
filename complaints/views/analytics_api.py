"""
AAWAJ Analytics API - Phase 2 analytics endpoints.
Handles hotspots, trends, heatmap, ward stats, severity, clusters, and duplicates.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..models import Complaint
from .helpers import role_required


@require_http_methods(["GET"])
def api_hotspots(request):
    """Get ranked hotspot clusters. Public endpoint."""
    from ..services import hotspot_service

    limit = int(request.GET.get('limit', 10))
    hotspots = hotspot_service.get_top_hotspots(limit=limit)
    return JsonResponse({'hotspots': hotspots, 'count': len(hotspots)})


@require_http_methods(["GET"])
def api_priority_zones(request):
    """Get population-normalized priority zone rankings."""
    from ..services import priority_engine

    zones = priority_engine.compute_ward_priority_scores()
    return JsonResponse({'zones': zones, 'count': len(zones)})


@require_http_methods(["GET"])
def api_analytics_heatmap(request):
    """Enhanced heatmap data with severity weighting and cluster overlays."""
    from ..services import clustering_service

    complaints = Complaint.objects.filter(
        status__in=['published', 'resolved']
    ).values(
        'latitude', 'longitude', 'ai_severity_score', 'category', 'ward'
    )

    heatmap_points = [
        {
            'lat': c['latitude'],
            'lng': c['longitude'],
            'intensity': c['ai_severity_score'] / 10.0,
            'category': c['category'],
        }
        for c in complaints
    ]

    clusters_geojson = clustering_service.get_clusters_geojson()

    return JsonResponse({
        'heatmap': heatmap_points,
        'clusters': clusters_geojson,
    })


@require_http_methods(["GET"])
def api_analytics_trends(request):
    """Temporal trend data (daily/weekly/monthly)."""
    from ..services import analytics_service

    days = int(request.GET.get('days', 30))
    granularity = request.GET.get('granularity', 'day')

    trends = analytics_service.get_temporal_trends(days=days, granularity=granularity)
    return JsonResponse({'trends': trends})


@require_http_methods(["GET"])
def api_analytics_ward_stats(request):
    """Per-ward complaint statistics."""
    from ..services import geo_service

    stats = geo_service.get_ward_statistics()
    return JsonResponse({'wards': stats, 'count': len(stats)})


@require_http_methods(["GET"])
def api_analytics_severity(request):
    """Severity distribution and critical issue concentration."""
    from ..services import analytics_service

    data = analytics_service.get_severity_distribution()
    return JsonResponse(data)


@require_http_methods(["GET"])
def api_clusters(request):
    """Raw cluster data for map visualization."""
    from ..services import clustering_service

    geojson = clustering_service.get_clusters_geojson()
    return JsonResponse(geojson)


@require_http_methods(["GET"])
@role_required('government')
def api_government_performance(request):
    """Government response time and efficiency metrics."""
    from ..services import analytics_service

    metrics = analytics_service.get_performance_metrics()
    return JsonResponse(metrics)


@require_http_methods(["GET"])
def api_analytics_duplicates(request):
    """Get duplicate complaint groups."""
    from ..services import duplicate_service

    groups = duplicate_service.get_duplicate_groups()
    # Serialize dates
    for g in groups:
        for c in g['complaints']:
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()
    return JsonResponse({'groups': groups, 'count': len(groups)})


@csrf_exempt
@require_http_methods(["POST"])
@role_required('government')
def api_analytics_refresh(request):
    """Trigger re-computation of clusters/hotspots/duplicates."""
    from ..services import clustering_service, hotspot_service, duplicate_service, spam_service, geo_service

    results = {}

    # Ward assignment
    unassigned = Complaint.objects.filter(ward='', status__in=['published', 'pending_review', 'resolved'])
    assigned = 0
    for c in unassigned:
        ward = geo_service.detect_ward(c.latitude, c.longitude)
        if ward:
            c.ward = ward
            c.save(update_fields=['ward'])
            assigned += 1
    results['wards_assigned'] = assigned

    # Clustering
    clusters = clustering_service.run_dbscan_clustering()
    saved = clustering_service.save_clusters(clusters)
    results['clusters_found'] = len(clusters)

    # Hotspot scoring
    hotspots = hotspot_service.compute_hotspot_scores()
    hotspot_service.save_hotspot_snapshot()
    results['hotspots_scored'] = len(hotspots)

    # Duplicates
    dup_count = duplicate_service.detect_duplicates()
    results['duplicates_found'] = dup_count

    # Trust scores
    updated = spam_service.update_all_trust_scores()
    results['trust_scores_updated'] = updated

    return JsonResponse({'success': True, 'results': results})
