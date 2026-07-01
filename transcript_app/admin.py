from django.contrib import admin
from .models import Transcript, TranscriptSegment


class TranscriptSegmentInline(admin.TabularInline):
    model = TranscriptSegment
    extra = 0
    readonly_fields = ['start_time', 'end_time', 'text', 'confidence']


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_type', 'language', 'status', 'created_at']
    list_filter = ['status', 'source_type', 'language']
    search_fields = ['full_text']
    readonly_fields = ['full_text', 'status', 'error_message', 'created_at', 'updated_at']
    inlines = [TranscriptSegmentInline]


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'transcript', 'start_time', 'end_time', 'text']
    search_fields = ['text']