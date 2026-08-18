from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from subtitle_maker.domain.models import AudioChunk, SubtitleSegment


class AudioExtractor(Protocol):
    def extract_chunks(self, video_path: Path, output_dir: Path) -> list[AudioChunk]: ...


class Transcriber(Protocol):
    def transcribe(self, chunk: AudioChunk) -> list[SubtitleSegment]: ...


class Translator(Protocol):
    def translate(self, segments: Sequence[SubtitleSegment]) -> list[SubtitleSegment]: ...


class SubtitleWriter(Protocol):
    def write(self, segments: Sequence[SubtitleSegment], output_path: Path) -> None: ...
