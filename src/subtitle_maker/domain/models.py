from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioChunk:
    index: int
    path: Path
    offset_seconds: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class SubtitleSegment:
    id: int
    start_seconds: float
    end_seconds: float
    source_text: str
    translated_text: str | None = None

    def with_translation(self, text: str) -> "SubtitleSegment":
        return replace(self, translated_text=text.strip())


@dataclass(frozen=True, slots=True)
class PipelineResult:
    output_path: Path
    segment_count: int

