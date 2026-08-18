import json
from collections.abc import Sequence

from openai import OpenAI
from pydantic import BaseModel

from subtitle_maker.domain.models import SubtitleSegment


class TranslationError(RuntimeError):
    pass


class TranslatedItem(BaseModel):
    id: int
    text: str


class TranslationBatch(BaseModel):
    items: list[TranslatedItem]


class OpenAIChineseTranslator:
    def __init__(self, client: OpenAI, model: str, batch_size: int = 30) -> None:
        self.client = client
        self.model = model
        self.batch_size = batch_size

    def translate(self, segments: Sequence[SubtitleSegment]) -> list[SubtitleSegment]:
        translated: list[SubtitleSegment] = []
        for start in range(0, len(segments), self.batch_size):
            batch = list(segments[start : start + self.batch_size])
            translated.extend(self._translate_batch(batch))
        return translated

    def _translate_batch(self, segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
        payload = [{"id": item.id, "english": item.source_text} for item in segments]
        response = self.client.responses.parse(
            model=self.model,
            instructions=(
                "You translate dialogue subtitles from English into natural Simplified Chinese. "
                "Use the surrounding lines for context, preserve names and tone, and keep each "
                "translation concise enough for on-screen reading. Return exactly one item for "
                "every input id. Never merge, split, omit, renumber, or explain lines."
            ),
            input=json.dumps(payload, ensure_ascii=False),
            text_format=TranslationBatch,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise TranslationError("The translation model returned no structured result")

        by_id = {item.id: item.text.strip() for item in parsed.items}
        expected_ids = {item.id for item in segments}
        if set(by_id) != expected_ids:
            raise TranslationError("The translation model returned mismatched subtitle ids")
        if any(not text for text in by_id.values()):
            raise TranslationError("The translation model returned an empty subtitle")
        return [item.with_translation(by_id[item.id]) for item in segments]

