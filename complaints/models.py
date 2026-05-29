"""
AAWAJ Complaint Models
Database models for the civic complaint reporting system.
Includes Phase 2 analytics models for smart governance.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User


class Complaint(models.Model):
    """Core complaint model - stores all citizen-reported issues."""

    STATUS_CHOICES = [
        ('pending_ai', 'Pending AI Analysis'),
        ('pending_review', 'Pending Moderation'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
        ('resolved', 'Resolved'),
    ]

    CATEGORY_CHOICES = [
        ('roads', 'Roads & Potholes'),
        ('garbage', 'Garbage & Waste'),
        ('water', 'Water & Drainage'),
        ('electricity', 'Electricity & Power'),
        ('health', 'Health Hazards'),
        ('education', 'Education & Schools'),
        ('corruption', 'Corruption'),
        ('infrastructure', 'Public Infrastructure'),
        ('other', 'Other'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Unique tracking code for citizens
    complaint_code = models.CharField(
        max_length=12, unique=True, editable=False,
        help_text="Unique tracking code (e.g., AAW-XXXXXX)"
    )

    # Complaint content
    description = models.TextField(
        blank=True, default='',
        help_text="Citizen's text description or AI-generated from audio"
    )
    ai_generated_report = models.TextField(
        blank=True, default='',
        help_text="AI-generated structured -report for government"
    )

    # Location
    location_text = models.CharField(
        max_length=500,
        help_text="Human-readable address"
    )
    latitude = models.FloatField(default=27.7172)
    longitude = models.FloatField(default=85.3240)

    # Ward assignment (Phase 2 — auto-detected from coordinates)
    ward = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Ward name auto-detected from GPS coordinates"
    )

    # Classification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_ai')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')

    # AI analysis results
    ai_verdict = models.CharField(
        max_length=20, blank=True, default='pending',
        help_text="AI confidence verdict: high, medium, low"
    )
    ai_confidence_score = models.FloatField(
        default=0.0,
        help_text="AI confidence score 0.0 - 1.0"
    )
    ai_category_detected = models.CharField(max_length=50, blank=True, default='')
    ai_is_fake = models.BooleanField(default=False)
    ai_urgency = models.BooleanField(
        default=False,
        help_text="True if AI detects emergency/urgent situation"
    )
    ai_severity_score = models.IntegerField(
        default=5,
        help_text="Severity score 1-10"
    )

    # Trust / spam score (Phase 2)
    trust_score = models.FloatField(
        default=1.0,
        help_text="Complaint trust score 0.0-1.0 (1.0 = fully trusted)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'

    def save(self, *args, **kwargs):
        if not self.complaint_code:
            self.complaint_code = f"AAW-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.complaint_code} - {self.get_category_display()} ({self.get_status_display()})"


class ComplaintImage(models.Model):
    """Images attached to a complaint."""
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='complaints/images/%Y/%m/')
    image_hash = models.CharField(
        max_length=64, blank=True, default='',
        db_index=True,
        help_text="Perceptual hash of image for duplicate detection"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Auto-calculate image hash on save if not already present."""
        if not self.image_hash and self.image:
            from .image_utils import calculate_image_hash
            try:
                self.image.seek(0)
                calculated_hash = calculate_image_hash(self.image)
                if calculated_hash:
                    self.image_hash = calculated_hash
                    print(f"[MODEL_SAVE] Auto-calculated hash for {self.complaint.complaint_code}: {self.image_hash}")
            except Exception as e:
                print(f"[MODEL_SAVE] Error calculating hash: {e}")
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.complaint.complaint_code}"


class ComplaintAudio(models.Model):
    """Audio recordings attached to a complaint."""
    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='audio_files'
    )
    audio_file = models.FileField(upload_to='complaints/audio/%Y/%m/')
    transcription = models.TextField(
        blank=True, default='',
        help_text="AI-transcribed text from audio"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audio for {self.complaint.complaint_code}"


class ModerationLog(models.Model):
    """Log of admin moderation actions."""
    ACTION_CHOICES = [
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('escalate', 'Escalated'),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='moderation_logs'
    )
    moderator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.complaint.complaint_code}"


class GovernmentAction(models.Model):
    """Government resolution actions on complaints."""
    ACTION_CHOICES = [
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('referred', 'Referred to Department'),
    ]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='government_actions'
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True, default='')
    officer_name = models.CharField(max_length=200, blank=True, default='')
    department = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.complaint.complaint_code}"


class ContactMessage(models.Model):
    """Messages submitted through the contact form."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=300, blank=True, default='')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.subject or 'No subject'} ({self.created_at.strftime('%Y-%m-%d')})"


# ============================================================
# PHASE 2 — SMART GOVERNANCE ANALYTICS MODELS
# ============================================================

class RegionPopulation(models.Model):
    """
    Ward/area population data for Kathmandu Valley.
    Used for population-normalized complaint prioritization.
    """
    ward_name = models.CharField(
        max_length=200, unique=True,
        help_text="Ward or area name (e.g., 'KMC Ward 1 - Naxal')"
    )
    ward_number = models.IntegerField(
        default=0,
        help_text="Numeric ward identifier"
    )
    municipality = models.CharField(
        max_length=200, default='Kathmandu Metropolitan City',
        help_text="Municipality this ward belongs to"
    )
    population = models.IntegerField(
        default=0,
        help_text="Estimated population count"
    )
    area_km2 = models.FloatField(
        default=1.0,
        help_text="Area in square kilometers"
    )
    center_latitude = models.FloatField(default=27.7172)
    center_longitude = models.FloatField(default=85.3240)
    population_density = models.FloatField(
        default=0.0,
        help_text="Auto-computed: population / area_km2"
    )

    class Meta:
        ordering = ['municipality', 'ward_number']
        verbose_name = 'Region Population'
        verbose_name_plural = 'Region Populations'

    def save(self, *args, **kwargs):
        if self.area_km2 > 0:
            self.population_density = self.population / self.area_km2
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ward_name} (Pop: {self.population:,})"


class ComplaintCluster(models.Model):
    """
    DBSCAN-generated complaint clusters / hotspot zones.
    Each record represents a geographic cluster of related complaints.
    """
    cluster_id = models.IntegerField(
        help_text="DBSCAN cluster label (-1 = noise)"
    )
    complaint_count = models.IntegerField(default=0)
    severity_average = models.FloatField(default=0.0)
    density_score = models.FloatField(
        default=0.0,
        help_text="Complaint density within cluster radius"
    )
    center_latitude = models.FloatField(default=27.7172)
    center_longitude = models.FloatField(default=85.3240)
    radius_meters = models.FloatField(
        default=0.0,
        help_text="Approximate radius of the cluster in meters"
    )
    hotspot_priority_score = models.FloatField(
        default=0.0,
        help_text="Population-normalized priority score"
    )
    dominant_category = models.CharField(
        max_length=20, blank=True, default='',
        help_text="Most common complaint category in this cluster"
    )
    category_breakdown = models.JSONField(
        default=dict, blank=True,
        help_text="Category counts: {'roads': 5, 'garbage': 3, ...}"
    )
    ward_name = models.CharField(max_length=200, blank=True, default='')
    unresolved_count = models.IntegerField(
        default=0,
        help_text="Number of unresolved complaints in this cluster"
    )

    # Timestamps
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-hotspot_priority_score']
        verbose_name = 'Complaint Cluster'
        verbose_name_plural = 'Complaint Clusters'

    def __str__(self):
        return f"Cluster #{self.cluster_id} — {self.complaint_count} complaints (Score: {self.hotspot_priority_score:.1f})"


class HotspotAnalytics(models.Model):
    """
    Historical hotspot records for trend tracking.
    Snapshots are taken each time analytics are computed.
    """
    cluster = models.ForeignKey(
        ComplaintCluster, on_delete=models.CASCADE,
        related_name='history', null=True, blank=True
    )
    ward_name = models.CharField(max_length=200, blank=True, default='')
    complaint_count = models.IntegerField(default=0)
    severity_average = models.FloatField(default=0.0)
    priority_score = models.FloatField(default=0.0)
    unresolved_count = models.IntegerField(default=0)
    snapshot_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-snapshot_date', '-priority_score']
        verbose_name = 'Hotspot Analytics'
        verbose_name_plural = 'Hotspot Analytics'

    def __str__(self):
        return f"{self.ward_name} — {self.snapshot_date} (Score: {self.priority_score:.1f})"


class ComplaintSimilarity(models.Model):
    """
    Links two complaints detected as duplicates/similar.
    Stores the method used and similarity score.
    """
    METHOD_CHOICES = [
        ('gps', 'GPS Proximity'),
        ('text', 'Text Similarity'),
        ('combined', 'Combined Score'),
    ]

    complaint_a = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='similar_from'
    )
    complaint_b = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name='similar_to'
    )
    similarity_score = models.FloatField(
        default=0.0,
        help_text="Similarity score 0.0 - 1.0"
    )
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='combined')
    gps_distance_meters = models.FloatField(
        default=0.0,
        help_text="Distance between the two complaints in meters"
    )
    text_similarity = models.FloatField(
        default=0.0,
        help_text="Text cosine similarity 0.0 - 1.0"
    )
    is_duplicate = models.BooleanField(
        default=False,
        help_text="True if system confidently considers these duplicates"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-similarity_score']
        unique_together = ['complaint_a', 'complaint_b']
        verbose_name = 'Complaint Similarity'
        verbose_name_plural = 'Complaint Similarities'

    def __str__(self):
        return f"{self.complaint_a.complaint_code} ↔ {self.complaint_b.complaint_code} ({self.similarity_score:.0%})"


class AnalyticsConfig(models.Model):
    """
    Singleton configuration for tunable analytics weights.
    Only one record should exist — enforced in save().
    """
    # Priority formula weights
    severity_weight = models.FloatField(default=1.5, help_text="Weight for severity score")
    urgency_weight = models.FloatField(default=2.0, help_text="Weight for urgent complaints")
    recency_weight = models.FloatField(default=1.2, help_text="Weight for recent complaints")
    verification_weight = models.FloatField(default=1.3, help_text="Weight for verified complaints")
    population_weight = models.FloatField(default=1.0, help_text="Population normalization factor")
    recurring_weight = models.FloatField(default=1.4, help_text="Weight for recurring/duplicate issues")

    # DBSCAN parameters
    dbscan_eps_meters = models.FloatField(
        default=300.0,
        help_text="DBSCAN radius in meters (epsilon parameter)"
    )
    dbscan_min_samples = models.IntegerField(
        default=3,
        help_text="Minimum complaints to form a cluster"
    )

    # Duplicate detection thresholds
    duplicate_radius_meters = models.FloatField(
        default=100.0,
        help_text="GPS proximity radius for duplicate detection"
    )
    duplicate_time_days = models.IntegerField(
        default=7,
        help_text="Time window (days) for duplicate detection"
    )
    duplicate_text_threshold = models.FloatField(
        default=0.5,
        help_text="Text similarity threshold for duplicate detection (0-1)"
    )

    # Spam thresholds
    spam_frequency_limit = models.IntegerField(
        default=5,
        help_text="Max complaints from same source in 24h before flagging"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Analytics Configuration'
        verbose_name_plural = 'Analytics Configuration'

    def save(self, *args, **kwargs):
        # Singleton: ensure only one config record exists
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion of singleton

    @classmethod
    def get_config(cls):
        """Get or create the singleton config."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Analytics Configuration"
