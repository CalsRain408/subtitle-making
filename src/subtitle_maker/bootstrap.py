from openai import OpenAI

from subtitle_maker.config import Settings
from subtitle_maker.domain.ports import Transcriber
from subtitle_maker.media.ffmpeg import FfmpegAudioExtractor, FfmpegSubtitleRenderer
from subtitle_maker.pipeline.service import SubtitlePipeline
from subtitle_maker.subtitles.ass import AssWriter
from subtitle_maker.subtitles.srt import SrtWriter
from subtitle_maker.transcription.mlx_whisper import MlxWhisperTranscriber
from subtitle_maker.transcription.openai_whisper import OpenAIWhisperTranscriber
from subtitle_maker.translation.openai_translator import OpenAIChineseTranslator


def build_pipeline(settings: Settings) -> SubtitlePipeline:
    client = OpenAI(api_key=settings.require_api_key(), max_retries=3, timeout=300.0)
    transcriber: Transcriber
    if settings.transcription_backend == "mlx":
        transcriber = MlxWhisperTranscriber(
            model=settings.local_transcription_model,
            language=settings.transcription_language,
        )
    else:
        transcriber = OpenAIWhisperTranscriber(
            client=client,
            model=settings.transcription_model,
        )
    return SubtitlePipeline(
        audio_extractor=FfmpegAudioExtractor(chunk_seconds=settings.audio_chunk_seconds),
        transcriber=transcriber,
        translator=OpenAIChineseTranslator(
            client=client,
            model=settings.translation_model,
            batch_size=settings.translation_batch_size,
        ),
        subtitle_writer=SrtWriter(),
        burn_subtitle_writer=AssWriter(
            chinese_font_name=settings.chinese_subtitle_font,
            english_font_name=settings.english_subtitle_font,
        ),
        video_renderer=FfmpegSubtitleRenderer(),
    )
