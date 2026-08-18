from pathlib import Path

from subtitle_maker.domain.models import PipelineResult, SubtitleSegment
from subtitle_maker.domain.ports import (
    AudioExtractor,
    SubtitleWriter,
    Transcriber,
    Translator,
    VideoRenderer,
)


class SubtitlePipeline:
    def __init__(
        self,
        audio_extractor: AudioExtractor,
        transcriber: Transcriber,
        translator: Translator,
        subtitle_writer: SubtitleWriter,
        burn_subtitle_writer: SubtitleWriter | None = None,
        video_renderer: VideoRenderer | None = None,
    ) -> None:
        self.audio_extractor = audio_extractor
        self.transcriber = transcriber
        self.translator = translator
        self.subtitle_writer = subtitle_writer
        self.burn_subtitle_writer = burn_subtitle_writer
        self.video_renderer = video_renderer

    def process(
        self,
        video_path: Path,
        output_path: Path,
        work_dir: Path,
        video_output_path: Path | None = None,
    ) -> PipelineResult:
        chunks = self.audio_extractor.extract_chunks(video_path, work_dir / "audio")

        all_segments: list[SubtitleSegment] = []
        for chunk in chunks:
            all_segments.extend(self.transcriber.transcribe(chunk))

        normalized = [
            SubtitleSegment(
                id=index,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                source_text=segment.source_text,
            )
            for index, segment in enumerate(all_segments)
        ]
        translated = self.translator.translate(normalized)
        self.subtitle_writer.write(translated, output_path)
        if video_output_path is not None:
            if self.burn_subtitle_writer is None or self.video_renderer is None:
                raise RuntimeError("Video subtitle rendering is not configured")
            burn_subtitle_path = work_dir / "subtitles.bilingual.ass"
            self.burn_subtitle_writer.write(translated, burn_subtitle_path)
            self.video_renderer.render(video_path, burn_subtitle_path, video_output_path)
        return PipelineResult(
            output_path=output_path,
            segment_count=len(translated),
            video_output_path=video_output_path,
        )
