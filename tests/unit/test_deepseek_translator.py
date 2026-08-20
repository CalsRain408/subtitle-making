import json
from types import SimpleNamespace
from typing import Any, cast
from unittest import TestCase
from unittest.mock import MagicMock

from openai import OpenAI

from subtitle_maker.domain.models import SubtitleSegment
from subtitle_maker.translation.deepseek_translator import DeepSeekChineseTranslator


class DeepSeekChineseTranslatorTest(TestCase):
    def test_translate_uses_adjacent_lines_as_context(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content='{"items":[{"id":1,"text":"你好。"}]}'
                        ),
                    )
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content='{"items":[{"id":2,"text":"再见。"}]}'
                        ),
                    )
                ]
            ),
        ]
        translator = DeepSeekChineseTranslator(
            client=cast(OpenAI, client),
            model="deepseek-v4-pro",
            batch_size=1,
            context_size=1,
        )
        segments = [
            SubtitleSegment(1, 0, 1, "Hello."),
            SubtitleSegment(2, 1, 2, "Goodbye."),
        ]

        result = translator.translate(segments)

        self.assertEqual([item.translated_text for item in result], ["你好。", "再见。"])
        first_call = cast(dict[str, Any], client.chat.completions.create.call_args_list[0].kwargs)
        payload = json.loads(first_call["messages"][1]["content"])
        self.assertEqual(
            payload,
            [
                {"id": 1, "english": "Hello.", "translate": True},
                {"id": 2, "english": "Goodbye.", "translate": False},
            ],
        )
        self.assertEqual(first_call["response_format"], {"type": "json_object"})
        self.assertEqual(first_call["extra_body"], {"thinking": {"type": "enabled"}})
