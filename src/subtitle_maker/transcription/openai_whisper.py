from collections.abc import Mapping
from typing import Any

from openai import OpenAI

from subtitle_maker.domain.models import AudioChunk, SubtitleSegment


class TranscriptionError(RuntimeError):
    pass


class OpenAIWhisperTranscriber:
    def __init__(self, client: OpenAI, model: str = "whisper-1") -> None:
        self.client = client
        self.model = model

    def transcribe(self, chunk: AudioChunk) -> list[SubtitleSegment]:
        with chunk.path.open("rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language="en",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                temperature=0,
            )

        raw_segments = getattr(response, "segments", None) or []
        normalized: list[SubtitleSegment] = []
        for local_index, item in enumerate(raw_segments):
            local_start = float(self._value(item, "start", 0.0))
            local_end = float(self._value(item, "end", local_start))
            start = local_start + chunk.offset_seconds
            end = local_end + chunk.offset_seconds
            text = str(self._value(item, "text", "")).strip()
            if not text:
                continue
            normalized.append(
                SubtitleSegment(
                    id=local_index,
                    start_seconds=start,
                    end_seconds=end,
                    source_text=text,
                )
            )

        if normalized:
            return normalized

        full_text = str(getattr(response, "text", "")).strip()
        if not full_text:
            return []
        if chunk.duration_seconds <= 0:
            raise TranscriptionError(f"No usable timestamps returned for {chunk.path.name}")
        return [
            SubtitleSegment(
                id=0,
                start_seconds=chunk.offset_seconds,
                end_seconds=chunk.offset_seconds + chunk.duration_seconds,
                source_text=full_text,
            )
        ]

    @staticmethod
    def _value(item: Any, key: str, default: Any) -> Any:
        if isinstance(item, Mapping):
            return item.get(key, default)
        return getattr(item, key, default)
