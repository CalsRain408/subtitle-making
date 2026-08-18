from collections.abc import Sequence
from pathlib import Path

from subtitle_maker.domain.models import SubtitleSegment


class SrtWriter:
    def write(self, segments: Sequence[SubtitleSegment], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(segments), encoding="utf-8")

    def render(self, segments: Sequence[SubtitleSegment]) -> str:
        blocks: list[str] = []
        for index, segment in enumerate(segments, start=1):
            start = max(0.0, segment.start_seconds)
            end = max(start + 0.1, segment.end_seconds)
            lines = [
                str(index),
                f"{self._timestamp(start)} --> {self._timestamp(end)}",
                self._clean(segment.source_text),
            ]
            if segment.translated_text:
                lines.append(self._clean(segment.translated_text))
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks) + ("\n" if blocks else "")

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join(text.replace("\r", " ").replace("\n", " ").split())

    @staticmethod
    def _timestamp(seconds: float) -> str:
        milliseconds = round(seconds * 1000)
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"

