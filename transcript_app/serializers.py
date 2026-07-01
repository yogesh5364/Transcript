from rest_framework import serializers
from .models import Transcript, TranscriptSegment


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    start_time_formatted = serializers.ReadOnlyField()
    end_time_formatted = serializers.ReadOnlyField()

    class Meta:
        model = TranscriptSegment
        fields = ['id', 'start_time', 'end_time', 'start_time_formatted', 'end_time_formatted', 'text', 'confidence']

class TranscriptSerializer(serializers.ModelSerializer):
    segments = TranscriptSegmentSerializer(many=True, read_only=True)

    class Meta:
        model = Transcript
        fields = [
            'id', 'audio_file', 'youtube_url', 'source_type',
            'language', 'status', 'full_text', 'error_message',
            'created_at', 'updated_at', 'segments'
        ]
        read_only_fields = ['status', 'full_text', 'error_message', 'created_at', 'updated_at']


class TranscriptUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = ['audio_file', 'youtube_url', 'source_type', 'language']