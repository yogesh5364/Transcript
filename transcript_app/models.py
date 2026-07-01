from django.db import models


class Transcript(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]

    SOURCE_CHOICES = [
        ('file', 'File Upload'),
        ('youtube', 'YouTube URL'),
        ('mic', 'Microphone'),
    ]

    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='file')
    language = models.CharField(max_length=10, default='hi')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    full_text = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transcript #{self.id} - {self.status}"


class TranscriptSegment(models.Model):
    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name='segments'
    )
    start_time = models.FloatField()
    end_time = models.FloatField()
    text = models.TextField()
    confidence = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['start_time']

    @property
    def start_time_formatted(self):
        minutes = int(self.start_time // 60)
        seconds = int(self.start_time % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def end_time_formatted(self):
        minutes = int(self.end_time // 60)
        seconds = int(self.end_time % 60)
        return f"{minutes}:{seconds:02d}"

    def __str__(self):
        return f"Segment {self.start_time}s - {self.end_time}s"