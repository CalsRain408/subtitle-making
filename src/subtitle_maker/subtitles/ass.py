from collections.abc import Sequence
from pathlib import Path
from sys import platform

from subtitle_maker.domain.models import SubtitleSegment


class AssWriter:
    """Writes styled subtitles for FFmpeg/libass video rendering."""

    _header_template = (
        """[Script Info]
Title: Subtitle Maker Bilingual Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, """
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Bilingual,{font_name},52,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,"
        "0,0,0,0,100,100,0,0,1,3,1,2,90,90,58,1\n"
        """

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    )

    def __init__(
        self,
        chinese_font_name: str | None = None,
        english_font_name: str = "Roboto",
    ) -> None:
        self.chinese_font_name = self._validate_font_name(
            chinese_font_name or self._default_chinese_font()
        )
        self.english_font_name = self._validate_font_name(english_font_name)

    def write(self, segments: Sequence[SubtitleSegment], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(segments), encoding="utf-8-sig")

    def render(self, segments: Sequence[SubtitleSegment]) -> str:
        dialogues: list[str] = []
        for segment in segments:
            start = max(0.0, segment.start_seconds)
            end = max(start + 0.1, segment.end_seconds)
            chinese = self._clean(segment.translated_text or "")
            english = self._clean(segment.source_text)
            english_with_style = f"{{\\fn{self.english_font_name}\\b400}}{english}"
            text = f"{chinese}\\N{english_with_style}" if chinese else english_with_style
            dialogues.append(
                f"Dialogue: 0,{self._timestamp(start)},{self._timestamp(end)},"
                f"Bilingual,,0,0,0,,{text}"
            )
        header = self._header_template.format(font_name=self.chinese_font_name)
        return header + "\n".join(dialogues) + ("\n" if dialogues else "")

    @staticmethod
    def _clean(text: str) -> str:
        cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        return cleaned.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

    @staticmethod
    def _timestamp(seconds: float) -> str:
        centiseconds = round(seconds * 100)
        hours, remainder = divmod(centiseconds, 360_000)
        minutes, remainder = divmod(remainder, 6_000)
        whole_seconds, centis = divmod(remainder, 100)
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centis:02d}"

    @staticmethod
    def _default_chinese_font() -> str:
        return "Hiragino Sans GB" if platform == "darwin" else "Noto Sans CJK SC"

    @staticmethod
    def _validate_font_name(font_name: str) -> str:
        selected_font = font_name.strip()
        if not selected_font or any(character in selected_font for character in ",{}\\\r\n"):
            raise ValueError("Subtitle font name is invalid")
        return selected_font
