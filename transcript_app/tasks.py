# import os
# import re
# from celery import shared_task
# from django.conf import settings
# from .models import Transcript, TranscriptSegment

# def clean_repetitive_text(text):
#     """Remove excessive word repetition (hallucination fix)"""
#     words = text.split()
#     cleaned = []
#     repeat_count = 0
#     for i, word in enumerate(words):
#         if i > 0 and word == words[i-1]:
#             repeat_count += 1
#             if repeat_count >= 3:
#                 continue
#         else:
#             repeat_count = 0
#         cleaned.append(word)
#     return ' '.join(cleaned)


# # def load_whisper_model():
# #     import whisper
# #     model_name = getattr(settings, 'WHISPER_MODEL', 'small')
# #     return whisper.load_model(model_name)

# # def load_whisper_model():
# #     from faster_whisper import WhisperModel
# #     model_name = getattr(settings, 'WHISPER_MODEL', 'small')
# #     return WhisperModel(model_name, device="cpu", compute_type="int8")

# # def load_whisper_model():
# #     from faster_whisper import WhisperModel
# #     model_name = getattr(settings, 'WHISPER_MODEL', 'small')
# #     return WhisperModel(
# #         model_name,
# #         device="cpu",
# #         compute_type="int8",
# #         cpu_threads=2,        # ← kam threads use karo
# #         num_workers=1,        # ← sirf 1 worker
# #     )

# def load_whisper_model():
#     from faster_whisper import WhisperModel
#     import torch

#     model_name = getattr(settings, 'WHISPER_MODEL', 'medium')

#     if torch.cuda.is_available():
#         device = "cuda"
#         compute_type = "float16"
#     else:
#         device = "cpu"
#         compute_type = "int8"

#     return WhisperModel(
#         model_name,
#         device=device,
#         compute_type=compute_type,
#         cpu_threads=2,
#         num_workers=1,
#     )


# @shared_task(bind=True, max_retries=3)
# def transcribe_audio_task(self, transcript_id):
#     try:
#         transcript = Transcript.objects.get(id=transcript_id)
#         transcript.status = 'processing'
#         transcript.save()

#         if transcript.source_type == 'youtube' and transcript.youtube_url:
#             import yt_dlp
#             audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', f'yt_{transcript_id}.mp3')
#             os.makedirs(os.path.dirname(audio_path), exist_ok=True)
#             ydl_opts = {
#                 'format': 'bestaudio/best',
#                 'outtmpl': audio_path.replace('.mp3', '.%(ext)s'),
#                 'postprocessors': [{
#                     'key': 'FFmpegExtractAudio',
#                     'preferredcodec': 'mp3',
#                 }],
#                 'quiet': True,
#                 'noplaylist': True,
#             }
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([transcript.youtube_url])

#         elif transcript.source_type == 'file' and transcript.audio_file:
#             audio_path = transcript.audio_file.path
#         else:
#             raise ValueError("No audio source found")

#         model = load_whisper_model()
#         language = transcript.language or 'hi'

#         segments_gen, info = model.transcribe(
#             audio_path,
#             language=language,
#             condition_on_previous_text=False,
#         )

#         full_text = ""
#         segments_list = []
#         for seg in segments_gen:
#             full_text += seg.text + " "
#             segments_list.append({
#                 'start': seg.start,
#                 'end': seg.end,
#                 'text': seg.text,
#                 'avg_logprob': seg.avg_logprob
#             })

#         result = {'text': full_text.strip(), 'segments': segments_list}

#         transcript.full_text = result['text']
#         transcript.status = 'done'
#         transcript.save()

#         TranscriptSegment.objects.filter(transcript=transcript).delete()
#         segments = []
#         last_text = None
#         repeat_segment_count = 0

#         for seg in result['segments']:
#             cleaned = clean_repetitive_text(seg['text'].strip())
            
#             if cleaned == last_text:
#                 repeat_segment_count += 1
#                 if repeat_segment_count >= 2:
#                     continue
#             else:
#                 repeat_segment_count = 0
            
#             last_text = cleaned
            
#             segments.append(TranscriptSegment(
#                 transcript=transcript,
#                 start_time=seg['start'],
#                 end_time=seg['end'],
#                 text=cleaned,
#                 confidence=seg.get('avg_logprob', None)
#             ))

#         TranscriptSegment.objects.bulk_create(segments)

#         return {'status': 'done', 'transcript_id': transcript_id}

#     except Transcript.DoesNotExist:
#         return {'status': 'failed', 'error': 'Transcript not found'}

#     except Exception as exc:
#         try:
#             transcript = Transcript.objects.get(id=transcript_id)
#             transcript.status = 'failed'
#             transcript.error_message = str(exc)
#             transcript.save()
#         except:
#             pass
#         raise self.retry(exc=exc, countdown=60)

import os
import re
from celery import shared_task
from django.conf import settings
from .models import Transcript, TranscriptSegment


def clean_repetitive_text(text):
    words = text.split()
    cleaned = []
    repeat_count = 0
    for i, word in enumerate(words):
        if i > 0 and word == words[i-1]:
            repeat_count += 1
            if repeat_count >= 3:
                continue
        else:
            repeat_count = 0
        cleaned.append(word)
    return ' '.join(cleaned)


def load_whisper_model():
    from faster_whisper import WhisperModel
    import torch

    model_name = getattr(settings, 'WHISPER_MODEL', 'medium')

    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"

    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=2,
        num_workers=1,
    )


@shared_task(bind=True, max_retries=0)
def transcribe_audio_task(self, transcript_id):
    try:
        transcript = Transcript.objects.get(id=transcript_id)
        transcript.status = 'processing'
        transcript.save()

        if transcript.source_type == 'youtube' and transcript.youtube_url:
            import yt_dlp
            audio_path = os.path.join(
                settings.MEDIA_ROOT, 'audio', f'yt_{transcript_id}.mp3'
            )
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path.replace('.mp3', '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'quiet': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([transcript.youtube_url])

        elif transcript.source_type == 'file' and transcript.audio_file:
            audio_path = transcript.audio_file.path
        else:
            raise ValueError("No audio source found")

        model = load_whisper_model()
        language = transcript.language or 'hi'

        # GPU pe large-v2, CPU pe medium
        import torch
        if torch.cuda.is_available():
            model_for_transcribe = 'large-v2'
        else:
            model_for_transcribe = getattr(settings, 'WHISPER_MODEL', 'medium')

        segments_gen, info = model.transcribe(
            audio_path,
            language=language,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
            beam_size=5,
            best_of=5,
            temperature=0.0,
            initial_prompt="यह हिंदी ऑडियो है। शब्द स्पष्ट रूप से लिखें।",
        )

        full_text = ""
        segments_list = []

        for seg in segments_gen:
            # Low confidence skip karo
            if seg.avg_logprob < -1.0:
                continue
            # No speech skip karo
            if seg.no_speech_prob > 0.6:
                continue

            cleaned = clean_repetitive_text(seg.text.strip())
            if not cleaned:
                continue

            full_text += cleaned + " "
            segments_list.append({
                'start': seg.start,
                'end': seg.end,
                'text': cleaned,
                'avg_logprob': seg.avg_logprob
            })

        result = {
            'text': full_text.strip(),
            'segments': segments_list
        }

        transcript.full_text = result['text']
        transcript.status = 'done'
        transcript.save()

        TranscriptSegment.objects.filter(transcript=transcript).delete()
        segments = []
        last_text = None
        repeat_segment_count = 0

        for seg in result['segments']:
            if seg['text'] == last_text:
                repeat_segment_count += 1
                if repeat_segment_count >= 2:
                    continue
            else:
                repeat_segment_count = 0
            last_text = seg['text']

            segments.append(TranscriptSegment(
                transcript=transcript,
                start_time=seg['start'],
                end_time=seg['end'],
                text=seg['text'],
                confidence=seg['avg_logprob']
            ))

        TranscriptSegment.objects.bulk_create(segments)
        return {'status': 'done', 'transcript_id': transcript_id}

    except Transcript.DoesNotExist:
        return {'status': 'failed', 'error': 'Transcript not found'}

    except Exception as exc:
        try:
            transcript = Transcript.objects.get(id=transcript_id)
            transcript.status = 'failed'
            transcript.error_message = str(exc)
            transcript.save()
        except:
            pass
        raise exc