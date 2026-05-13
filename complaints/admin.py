"""
AAWAJ Admin Configuration.
Includes Phase 2 analytics models.
"""

from django.contrib import admin
from .models import (
    Complaint, ComplaintImage, ComplaintAudio, ModerationLog,
    GovernmentAction, ContactMessage,
    RegionPopulation, ComplaintCluster, HotspotAnalytics,
    ComplaintSimilarity, AnalyticsConfig
)


class ComplaintImageInline(admin.TabularInline):
    model = ComplaintImage
    extra = 0


class ComplaintAudioInline(admin.TabularInline):
    model = ComplaintAudio
    extra = 0


class ModerationLogInline(admin.TabularInline):
    model = ModerationLog
    extra = 0
    readonly_fields = ['created_at']


class GovernmentActionInline(admin.TabularInline):
    model = GovernmentAction
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = [
        'complaint_code', 'category', 'status', 'priority',
        'location_text', 'ward', 'ai_verdict', 'ai_confidence_score',
        'trust_score', 'created_at'
    ]
    list_filter = ['status', 'category', 'priority', 'ai_verdict', 'ward']
    search_fields = ['complaint_code', 'description', 'location_text', 'ward']
    readonly_fields = ['complaint_code', 'created_at', 'updated_at']
    inlines = [ComplaintImageInline, ComplaintAudioInline, ModerationLogInline, GovernmentActionInline]


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ['complaint', 'moderator', 'action', 'created_at']
    list_filter = ['action']


@admin.register(GovernmentAction)
class GovernmentActionAdmin(admin.ModelAdmin):
    list_display = ['complaint', 'action_type', 'officer_name', 'department', 'created_at']
    list_filter = ['action_type']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at']


# ============================================================
# PHASE 2 — ANALYTICS MODELS
# ============================================================

@admin.register(RegionPopulation)
class RegionPopulationAdmin(admin.ModelAdmin):
    list_display = ['ward_name', 'ward_number', 'municipality', 'population',
                    'area_km2', 'population_density']
    list_filter = ['municipality']
    search_fields = ['ward_name']
    ordering = ['municipality', 'ward_number']


@admin.register(ComplaintCluster)
class ComplaintClusterAdmin(admin.ModelAdmin):
    list_display = ['cluster_id', 'complaint_count', 'severity_average',
                    'hotspot_priority_score', 'dominant_category', 'ward_name', 'computed_at']
    list_filter = ['dominant_category', 'ward_name']
    ordering = ['-hotspot_priority_score']


@admin.register(HotspotAnalytics)
class HotspotAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['ward_name', 'complaint_count', 'severity_average',
                    'priority_score', 'unresolved_count', 'snapshot_date']
    list_filter = ['ward_name', 'snapshot_date']
    ordering = ['-snapshot_date', '-priority_score']


@admin.register(ComplaintSimilarity)
class ComplaintSimilarityAdmin(admin.ModelAdmin):
    list_display = ['complaint_a', 'complaint_b', 'similarity_score',
                    'method', 'gps_distance_meters', 'is_duplicate']
    list_filter = ['method', 'is_duplicate']
    ordering = ['-similarity_score']


@admin.register(AnalyticsConfig)
class AnalyticsConfigAdmin(admin.ModelAdmin):
    list_display = ['severity_weight', 'urgency_weight', 'dbscan_eps_meters',
                    'dbscan_min_samples', 'updated_at']

    def has_add_permission(self, request):
        # Only allow one config record (singleton)
        return not AnalyticsConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
