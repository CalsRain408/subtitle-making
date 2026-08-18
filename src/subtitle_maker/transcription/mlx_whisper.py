from collections.abc import Mapping
from importlib import import_module
from threading import Lock
from typing import Any, Protocol, cast

from subtitle_maker.domain.models import AudioChunk, SubtitleSegment
from subtitle_maker.transcription import TranscriptionError

_MLX_INFERENCE_LOCK = Lock()


class _MlxWhisperModule(Protocol):
    def transcribe(self, audio: str, **kwargs: Any) -> Mapping[str, Any]: ...


class MlxWhisperTranscriber:
    """Runs Whisper locally with Apple's MLX runtime on Apple Silicon."""

    def __init__(
        self,
        model: str = "mlx-community/whisper-turbo",
        language: str = "en",
    ) -> None:
        self.model = model
        self.language = language

    def transcribe(self, chunk: AudioChunk) -> list[SubtitleSegment]:
        try:
            mlx_whisper = cast(_MlxWhisperModule, import_module("mlx_whisper"))
        except ImportError as exc:
            raise TranscriptionError(
                "Local Whisper is not installed. Run "
                "'python -m pip install -e \".[local]\"' on an Apple Silicon Mac."
            ) from exc

        # MLX uses unified GPU memory. Serializing inference prevents two web jobs
        # from loading/decoding the model concurrently and exhausting that memory.
        with _MLX_INFERENCE_LOCK:
            response = mlx_whisper.transcribe(
                str(chunk.path),
                path_or_hf_repo=self.model,
                language=self.language,
                task="transcribe",
                temperature=0.0,
                condition_on_previous_text=True,
                word_timestamps=False,
                fp16=True,
                verbose=None,
            )

        raw_segments = self._value(response, "segments", []) or []
        normalized: list[SubtitleSegment] = []
        for local_index, item in enumerate(raw_segments):
            local_start = float(self._value(item, "start", 0.0))
            local_end = float(self._value(item, "end", local_start))
            text = str(self._value(item, "text", "")).strip()
            if not text:
                continue
            normalized.append(
                SubtitleSegment(
                    id=local_index,
                    start_seconds=local_start + chunk.offset_seconds,
                    end_seconds=local_end + chunk.offset_seconds,
                    source_text=text,
                )
            )

        if normalized:
            return normalized

        full_text = str(self._value(response, "text", "")).strip()
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
