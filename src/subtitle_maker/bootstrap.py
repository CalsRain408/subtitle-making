from openai import OpenAI

from subtitle_maker.config import Settings
from subtitle_maker.domain.ports import Transcriber
from subtitle_maker.media.ffmpeg import FfmpegAudioExtractor, FfmpegSubtitleRenderer
from subtitle_maker.pipeline.service import SubtitlePipeline
from subtitle_maker.subtitles.ass import AssWriter
from subtitle_maker.subtitles.srt import SrtWriter
from subtitle_maker.transcription.mlx_whisper import MlxWhisperTranscriber
from subtitle_maker.transcription.openai_whisper import OpenAIWhisperTranscriber
from subtitle_maker.translation.deepseek_translator import DeepSeekChineseTranslator


def build_translator(settings: Settings) -> DeepSeekChineseTranslator:
    client = OpenAI(
        api_key=settings.require_deepseek_api_key(),
        base_url=settings.deepseek_base_url,
        max_retries=3,
        timeout=300.0,
    )
    return DeepSeekChineseTranslator(
        client=client,
        model=settings.translation_model,
        batch_size=settings.translation_batch_size,
        reasoning_effort=settings.translation_reasoning_effort,
        thinking=settings.translation_thinking,
        max_output_tokens=settings.translation_max_output_tokens,
    )


def build_pipeline(settings: Settings) -> SubtitlePipeline:
    transcriber: Transcriber
    if settings.transcription_backend == "mlx":
        transcriber = MlxWhisperTranscriber(
            model=settings.local_transcription_model,
            language=settings.transcription_language,
        )
    else:
        client = OpenAI(
            api_key=settings.require_openai_api_key(), max_retries=3, timeout=300.0
        )
        transcriber = OpenAIWhisperTranscriber(
            client=client,
            model=settings.transcription_model,
        )
    return SubtitlePipeline(
        audio_extractor=FfmpegAudioExtractor(chunk_seconds=settings.audio_chunk_seconds),
        transcriber=transcriber,
        translator=build_translator(settings),
        subtitle_writer=SrtWriter(),
        burn_subtitle_writer=AssWriter(
            chinese_font_name=settings.chinese_subtitle_font,
            english_font_name=settings.english_subtitle_font,
        ),
        video_renderer=FfmpegSubtitleRenderer(),
    )
