from unittest import TestCase

from subtitle_maker.domain.models import SubtitleSegment
from subtitle_maker.subtitles.srt import SrtReader, SrtWriter


class SrtWriterTest(TestCase):
    def test_render_bilingual_srt(self) -> None:
        result = SrtWriter().render(
            [
                SubtitleSegment(
                    id=99,
                    start_seconds=1.234,
                    end_seconds=3.5,
                    source_text="Where are you going?",
                    translated_text="你要去哪里？",
                )
            ]
        )

        self.assertEqual(
            result,
            (
                "1\n"
                "00:00:01,234 --> 00:00:03,500\n"
                "Where are you going?\n"
                "你要去哪里？\n"
            ),
        )

    def test_render_cleans_embedded_line_breaks(self) -> None:
        segment = SubtitleSegment(
            id=0,
            start_seconds=-1,
            end_seconds=0,
            source_text="  Hello\n  there ",
            translated_text="你好\r\n啊",
        )

        result = SrtWriter().render([segment])

        self.assertIn("00:00:00,000 --> 00:00:00,100", result)
        self.assertIn("Hello there\n你好 啊", result)


class SrtReaderTest(TestCase):
    def test_parse_english_srt(self) -> None:
        result = SrtReader().parse(
            "1\r\n"
            "00:00:01,250 --> 00:00:03,500\r\n"
            "Where are you\r\n"
            "going?\r\n"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].start_seconds, 1.25)
        self.assertEqual(result[0].end_seconds, 3.5)
        self.assertEqual(result[0].source_text, "Where are you going?")
