"""
AAWAJ Serializers - Django REST Framework serializers for API endpoints.
"""

from rest_framework import serializers
from .models import Complaint, ComplaintImage, ComplaintAudio, ModerationLog, GovernmentAction


class ComplaintImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintImage
        fields = ['id', 'image', 'image_url', 'uploaded_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        elif obj.image:
            return obj.image.url
        return None


class ComplaintAudioSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = ComplaintAudio
        fields = ['id', 'audio_file', 'audio_url', 'transcription', 'uploaded_at']

    def get_audio_url(self, obj):
        request = self.context.get('request')
        if obj.audio_file and request:
            return request.build_absolute_uri(obj.audio_file.url)
        elif obj.audio_file:
            return obj.audio_file.url
        return None


class ModerationLogSerializer(serializers.ModelSerializer):
    moderator_name = serializers.SerializerMethodField()

    class Meta:
        model = ModerationLog
        fields = ['id', 'action', 'notes', 'moderator_name', 'created_at']

    def get_moderator_name(self, obj):
        return obj.moderator.username if obj.moderator else 'System'


class GovernmentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentAction
        fields = ['id', 'action_type', 'notes', 'officer_name', 'department', 'created_at']


class ComplaintListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    first_image = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            'id', 'complaint_code', 'description', 'location_text',
            'latitude', 'longitude', 'status', 'status_display',
            'category', 'category_display', 'priority', 'priority_display',
            'ai_verdict', 'ai_confidence_score', 'ai_severity_score',
            'ai_urgency', 'first_image', 'image_count', 'created_at'
        ]

    def get_first_image(self, obj):
        first = obj.images.first()
        if first and first.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None

    def get_image_count(self, obj):
        return obj.images.count()


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """Full serializer with all related data."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    images = ComplaintImageSerializer(many=True, read_only=True)
    audio_files = ComplaintAudioSerializer(many=True, read_only=True)
    moderation_logs = ModerationLogSerializer(many=True, read_only=True)
    government_actions = GovernmentActionSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'id', 'complaint_code', 'description', 'ai_generated_report',
            'location_text', 'latitude', 'longitude',
            'status', 'status_display', 'category', 'category_display',
            'priority', 'priority_display',
            'ai_verdict', 'ai_confidence_score', 'ai_category_detected',
            'ai_is_fake', 'ai_urgency', 'ai_severity_score',
            'images', 'audio_files', 'moderation_logs', 'government_actions',
            'created_at', 'updated_at'
        ]


class ComplaintSubmitSerializer(serializers.Serializer):
    """Serializer for complaint submission."""
    description = serializers.CharField(required=False, allow_blank=True, default='')
    location_text = serializers.CharField(required=True)
    latitude = serializers.FloatField(required=False, default=27.7172)
    longitude = serializers.FloatField(required=False, default=85.3240)
    images = serializers.ListField(
        child=serializers.ImageField(), required=True, min_length=1
    )
    audio = serializers.FileField(required=False, allow_null=True)
