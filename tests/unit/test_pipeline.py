from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from subtitle_maker.domain.models import AudioChunk, SubtitleSegment
from subtitle_maker.pipeline.service import SubtitlePipeline
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
