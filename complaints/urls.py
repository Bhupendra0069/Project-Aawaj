"""
AAWAJ Complaints App URL Configuration.
Includes Phase 2 analytics API routes.
"""

from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/complaints/submit/', views.api_submit_complaint, name='api_submit'),
    path('api/complaints/<str:code>/status/', views.api_complaint_status, name='api_status'),
    path('api/complaints/public/', views.api_public_complaints, name='api_public'),
    path('api/dashboard/stats/', views.api_dashboard_stats, name='api_stats'),
    path('api/map/data/', views.api_map_data, name='api_map'),

    # Contact form API
    path('api/contact/submit/', views.api_contact_submit, name='api_contact'),

    # Moderation API
    path('api/moderation/queue/', views.api_moderation_queue, name='api_mod_queue'),
    path('api/moderation/<int:complaint_id>/action/', views.api_moderation_action, name='api_mod_action'),
    path('api/moderation/<int:complaint_id>/detail/', views.api_moderation_detail, name='api_mod_detail'),

    # Government API
    path('api/government/complaints/', views.api_government_complaints, name='api_gov_complaints'),
    path('api/government/export/csv/', views.api_government_export_csv, name='api_gov_csv'),
    path('api/government/<int:complaint_id>/detail/', views.api_government_detail, name='api_gov_detail'),
    path('api/government/<int:complaint_id>/action/', views.api_government_action, name='api_gov_action'),
    path('api/government/<int:complaint_id>/report/download/', views.api_government_download_report, name='api_gov_report'),
    path('api/government/performance/', views.api_government_performance, name='api_gov_performance'),

    # AI Analysis
    path('api/ai/analyze-image/', views.api_ai_analyze_image, name='api_ai_analyze'),

    # Phase 2 — Analytics API
    path('api/hotspots/', views.api_hotspots, name='api_hotspots'),
    path('api/analytics/priority-zones/', views.api_priority_zones, name='api_priority_zones'),
    path('api/analytics/heatmap/', views.api_analytics_heatmap, name='api_analytics_heatmap'),
    path('api/analytics/trends/', views.api_analytics_trends, name='api_analytics_trends'),
    path('api/analytics/ward-stats/', views.api_analytics_ward_stats, name='api_analytics_ward_stats'),
    path('api/analytics/severity/', views.api_analytics_severity, name='api_analytics_severity'),
    path('api/analytics/duplicates/', views.api_analytics_duplicates, name='api_analytics_duplicates'),
    path('api/analytics/refresh/', views.api_analytics_refresh, name='api_analytics_refresh'),
    path('api/clusters/', views.api_clusters, name='api_clusters'),
]
