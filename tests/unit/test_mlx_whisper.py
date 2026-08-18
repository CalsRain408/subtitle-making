import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from subtitle_maker.domain.models import AudioChunk
from subtitle_maker.transcription.mlx_whisper import MlxWhisperTranscriber


class MlxWhisperTranscriberTest(TestCase):
    def test_transcribe_offsets_segments_and_uses_episode_defaults(self) -> None:
        transcribe = Mock(
            return_value={
                "text": " Hello. ",
                "segments": [
                    {"start": 1.25, "end": 3.5, "text": " Hello. "},
                    {"start": 4.0, "end": 5.0, "text": "   "},
                ],
            }
        )
        fake_module = SimpleNamespace(transcribe=transcribe)
        chunk = AudioChunk(
            index=2,
            path=Path("part_002.mp3"),
            offset_seconds=1800.0,
            duration_seconds=900.0,
        )

        with patch.dict(sys.modules, {"mlx_whisper": fake_module}):
            result = MlxWhisperTranscriber().transcribe(chunk)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start_seconds, 1801.25)
        self.assertEqual(result[0].end_seconds, 1803.5)
        self.assertEqual(result[0].source_text, "Hello.")
        transcribe.assert_called_once_with(
            "part_002.mp3",
            path_or_hf_repo="mlx-community/whisper-turbo",
            language="en",
            task="transcribe",
            temperature=0.0,
            condition_on_previous_text=True,
            word_timestamps=False,
            fp16=True,
            verbose=None,
        )

    def test_transcribe_uses_chunk_duration_when_only_full_text_is_returned(self) -> None:
        fake_module = SimpleNamespace(
            transcribe=Mock(return_value={"text": "Fallback text", "segments": []})
        )
        chunk = AudioChunk(
            index=0,
            path=Path("part_000.mp3"),
            offset_seconds=15.0,
            duration_seconds=30.0,
        )

        with patch.dict(sys.modules, {"mlx_whisper": fake_module}):
            result = MlxWhisperTranscriber().transcribe(chunk)

        self.assertEqual(result[0].start_seconds, 15.0)
        self.assertEqual(result[0].end_seconds, 45.0)
