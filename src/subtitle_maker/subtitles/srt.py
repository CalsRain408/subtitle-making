import re
from collections.abc import Sequence
from pathlib import Path

from subtitle_maker.domain.models import SubtitleSegment


class SrtParseError(ValueError):
    pass


class SrtReader:
    _TIMESTAMP_PATTERN = re.compile(
        r"^(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+"
        r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
    )

    def read(self, input_path: Path) -> list[SubtitleSegment]:
        return self.parse(input_path.read_text(encoding="utf-8-sig"))

    def parse(self, content: str) -> list[SubtitleSegment]:
        normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return []

        segments: list[SubtitleSegment] = []
        for position, block in enumerate(re.split(r"\n\s*\n", normalized), start=1):
            lines = block.splitlines()
            if len(lines) < 3:
                raise SrtParseError(f"Invalid SRT block {position}: expected at least 3 lines")
            try:
                segment_id = int(lines[0].strip())
            except ValueError as exc:
                raise SrtParseError(
                    f"Invalid SRT block {position}: subtitle index is not an integer"
                ) from exc

            match = self._TIMESTAMP_PATTERN.match(lines[1].strip())
            if match is None:
                raise SrtParseError(f"Invalid SRT block {position}: malformed timestamp")
            text = " ".join(line.strip() for line in lines[2:] if line.strip())
            if not text:
                raise SrtParseError(f"Invalid SRT block {position}: subtitle text is empty")
            segments.append(
                SubtitleSegment(
                    id=segment_id,
                    start_seconds=self._seconds(match.group("start")),
                    end_seconds=self._seconds(match.group("end")),
                    source_text=text,
                )
            )
        return segments

    @staticmethod
    def _seconds(timestamp: str) -> float:
        hours, minutes, remainder = timestamp.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(remainder)


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
