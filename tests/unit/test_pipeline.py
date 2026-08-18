from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from subtitle_maker.domain.models import AudioChunk, SubtitleSegment
from subtitle_maker.pipeline.service import SubtitlePipeline
from subtitle_maker.subtitles.ass import AssWriter
from subtitle_maker.subtitles.srt import SrtWriter


class FakeExtractor:
    def extract_chunks(self, video_path: Path, output_dir: Path) -> list[AudioChunk]:
        return [AudioChunk(index=0, path=video_path, offset_seconds=0, duration_seconds=10)]


class FakeTranscriber:
    def transcribe(self, chunk: AudioChunk) -> list[SubtitleSegment]:
        return [SubtitleSegment(42, 1, 2, "Hello.")]


class FakeTranslator:
    def translate(self, segments: Sequence[SubtitleSegment]) -> list[SubtitleSegment]:
        return [segment.with_translation("你好。") for segment in segments]


class FakeVideoRenderer:
    def __init__(self) -> None:
        self.subtitle_content = ""

    def render(self, video_path: Path, subtitle_path: Path, output_path: Path) -> None:
        self.subtitle_content = subtitle_path.read_text(encoding="utf-8-sig")
        output_path.write_bytes(b"rendered video")


class PipelineTest(TestCase):
    def test_pipeline_reindexes_and_writes_output(self) -> None:
        with TemporaryDirectory() as directory:
            temp_path = Path(directory)
            output = temp_path / "result.srt"
            pipeline = SubtitlePipeline(
                audio_extractor=FakeExtractor(),
                transcriber=FakeTranscriber(),
                translator=FakeTranslator(),
                subtitle_writer=SrtWriter(),
            )

            result = pipeline.process(temp_path / "video.mp4", output, temp_path / "work")

            self.assertEqual(result.segment_count, 1)
            self.assertIn("Hello.\n你好。", output.read_text(encoding="utf-8"))

    def test_pipeline_renders_video_with_chinese_above_english(self) -> None:
        with TemporaryDirectory() as directory:
            temp_path = Path(directory)
            output = temp_path / "result.srt"
            video_output = temp_path / "result.mp4"
            renderer = FakeVideoRenderer()
            pipeline = SubtitlePipeline(
                audio_extractor=FakeExtractor(),
                transcriber=FakeTranscriber(),
                translator=FakeTranslator(),
                subtitle_writer=SrtWriter(),
                burn_subtitle_writer=AssWriter(),
                video_renderer=renderer,
            )

            result = pipeline.process(
                temp_path / "video.mp4",
                output,
                temp_path / "work",
                video_output,
            )

            self.assertEqual(result.video_output_path, video_output)
            self.assertEqual(video_output.read_bytes(), b"rendered video")
            self.assertIn(r"你好。\N{\fnRoboto\b400}Hello.", renderer.subtitle_content)
