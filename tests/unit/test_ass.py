from unittest import TestCase

from subtitle_maker.domain.models import SubtitleSegment
from subtitle_maker.subtitles.ass import AssWriter


class AssWriterTest(TestCase):
    def test_render_places_chinese_above_english(self) -> None:
        result = AssWriter(chinese_font_name="Hiragino Sans GB").render(
            [
                SubtitleSegment(
                    id=0,
                    start_seconds=1.234,
                    end_seconds=3.5,
                    source_text="Where are you going?",
                    translated_text="你要去哪里？",
                )
            ]
        )

        self.assertIn("Dialogue: 0,0:00:01.23,0:00:03.50", result)
        self.assertIn(r"你要去哪里？\N{\fnRoboto\b400}Where are you going?", result)
        self.assertIn("Alignment, MarginL, MarginR, MarginV", result)
        self.assertIn("Style: Bilingual,Hiragino Sans GB", result)

    def test_render_escapes_ass_override_characters(self) -> None:
        segment = SubtitleSegment(0, 0, 1, r"Use {name} \ value", "使用 {名字}")

        result = AssWriter().render([segment])

        self.assertIn(
            r"使用 \{名字\}\N{\fnRoboto\b400}Use \{name\} \\ value",
            result,
        )

    def test_render_accepts_an_installed_font_override(self) -> None:
        result = AssWriter(chinese_font_name="Noto Sans CJK SC").render([])

        self.assertIn("Style: Bilingual,Noto Sans CJK SC", result)

    def test_render_uses_configured_english_font_at_weight_400(self) -> None:
        segment = SubtitleSegment(0, 0, 1, "Hello", "你好")

        result = AssWriter(english_font_name="Roboto Flex").render([segment])

        self.assertIn(r"{\fnRoboto Flex\b400}Hello", result)
