import os
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from .models import Transcript, TranscriptSegment
from .serializers import TranscriptSerializer, TranscriptUploadSerializer
from .tasks import transcribe_audio_task
from django.shortcuts import render

def frontend_view(request):
    return render(request, 'transcript_app/index.html')


class TranscriptUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = TranscriptUploadSerializer(data=request.data)
        if serializer.is_valid():
            transcript = serializer.save()
            transcribe_audio_task.delay(transcript.id)
            return Response({
                'id': transcript.id,
                'status': 'pending',
                'message': 'Processing shuru ho gaya!'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TranscriptListView(APIView):
    def get(self, request):
        transcripts = Transcript.objects.all()
        serializer = TranscriptSerializer(transcripts, many=True)
        return Response(serializer.data)


class TranscriptDetailView(APIView):
    def get(self, request, pk):
        try:
            transcript = Transcript.objects.get(pk=pk)
            serializer = TranscriptSerializer(transcript)
            return Response(serializer.data)
        except Transcript.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            transcript = Transcript.objects.get(pk=pk)
            transcript.delete()
            return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
        except Transcript.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class TranscriptStatusView(APIView):
    def get(self, request, pk):
        try:
            transcript = Transcript.objects.get(pk=pk)
            return Response({
                'id': transcript.id,
                'status': transcript.status,
                'error_message': transcript.error_message
            })
        except Transcript.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class TranscriptExportView(APIView):
    def get(self, request, pk, format_type):
        try:
            transcript = Transcript.objects.get(pk=pk)
            if transcript.status != 'done':
                return Response({'error': 'Transcript not ready'}, status=status.HTTP_400_BAD_REQUEST)

            segments = transcript.segments.all()

            if format_type == 'txt':
                content = transcript.full_text
                response = HttpResponse(content, content_type='text/plain')
                response['Content-Disposition'] = f'attachment; filename="transcript_{pk}.txt"'
                return response

            elif format_type == 'srt':
                lines = []
                for i, seg in enumerate(segments, 1):
                    start = _seconds_to_srt_time(seg.start_time)
                    end = _seconds_to_srt_time(seg.end_time)
                    lines.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
                content = '\n'.join(lines)
                response = HttpResponse(content, content_type='text/plain')
                response['Content-Disposition'] = f'attachment; filename="transcript_{pk}.srt"'
                return response

            elif format_type == 'json':
                data = TranscriptSerializer(transcript).data
                import json
                response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2), content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="transcript_{pk}.json"'
                return response

            else:
                return Response({'error': 'Invalid format'}, status=status.HTTP_400_BAD_REQUEST)

        except Transcript.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


def _seconds_to_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"