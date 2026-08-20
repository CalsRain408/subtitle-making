import json
from collections.abc import Sequence
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from subtitle_maker.domain.models import SubtitleSegment


class TranslationError(RuntimeError):
    pass


class TranslatedItem(BaseModel):
    id: int
    text: str


class TranslationBatch(BaseModel):
    items: list[TranslatedItem]


class DeepSeekChineseTranslator:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        batch_size: int = 30,
        reasoning_effort: Literal["high", "max"] = "high",
        thinking: Literal["enabled", "disabled"] = "enabled",
        max_output_tokens: int = 8192,
        context_size: int = 3,
        response_attempts: int = 2,
    ) -> None:
        self.client = client
        self.model = model
        self.batch_size = batch_size
        self.reasoning_effort = reasoning_effort
        self.thinking = thinking
        self.max_output_tokens = max_output_tokens
        self.context_size = context_size
        self.response_attempts = response_attempts

    def translate(self, segments: Sequence[SubtitleSegment]) -> list[SubtitleSegment]:
        translated: list[SubtitleSegment] = []
        for start in range(0, len(segments), self.batch_size):
            targets = list(segments[start : start + self.batch_size])
            context_start = max(0, start - self.context_size)
            context_end = min(len(segments), start + self.batch_size + self.context_size)
            context = list(segments[context_start:context_end])
            translated.extend(self._translate_batch(targets, context))
        return translated

    def _translate_batch(
        self,
        targets: list[SubtitleSegment],
        context: list[SubtitleSegment],
    ) -> list[SubtitleSegment]:
        last_error: TranslationError | None = None
        for _ in range(self.response_attempts):
            try:
                return self._request_batch(targets, context)
            except TranslationError as exc:
                last_error = exc
        if last_error is None:
            raise TranslationError("DeepSeek response attempts must be at least one")
        raise last_error

    def _request_batch(
        self,
        targets: list[SubtitleSegment],
        context: list[SubtitleSegment],
    ) -> list[SubtitleSegment]:
        target_ids = {item.id for item in targets}
        payload = [
            {
                "id": item.id,
                "english": item.source_text,
                "translate": item.id in target_ids,
            }
            for item in context
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional subtitle translator for English-language TV "
                        "series. Translate dialogue into natural, concise Simplified Chinese "
                        "using surrounding lines for context. Preserve character names, jokes, "
                        "tone, implications, and continuity. Do not add explanations. The input "
                        "is a JSON array. Rows with translate=false are context only. Return a "
                        "JSON object containing exactly one item for every translate=true row, "
                        "with no context-only rows. Never merge, split, omit, or renumber rows. "
                        'Required JSON shape: {"items":[{"id":1,"text":"中文翻译"}]}.'
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            max_tokens=self.max_output_tokens,
            reasoning_effort=self.reasoning_effort,
            extra_body={"thinking": {"type": self.thinking}},
            stream=False,
        )
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise TranslationError(
                f"DeepSeek stopped before completing the batch: {choice.finish_reason}"
            )
        content = choice.message.content
        if not content or not content.strip():
            raise TranslationError("DeepSeek returned empty translation content")
        try:
            parsed = TranslationBatch.model_validate_json(content)
        except ValidationError as exc:
            raise TranslationError("DeepSeek returned an invalid translation JSON object") from exc

        returned_ids = [item.id for item in parsed.items]
        if len(returned_ids) != len(targets) or set(returned_ids) != target_ids:
            raise TranslationError("DeepSeek returned mismatched or duplicate subtitle ids")
        by_id = {item.id: item.text.strip() for item in parsed.items}
        if any(not text for text in by_id.values()):
            raise TranslationError("DeepSeek returned an empty subtitle translation")
        return [item.with_translation(by_id[item.id]) for item in targets]
