import shutil
import subprocess
from pathlib import Path

from subtitle_maker.domain.models import AudioChunk


class MediaProcessingError(RuntimeError):
    pass


class FfmpegAudioExtractor:
    """Extracts small mono MP3 chunks suitable for the transcription API."""

    def __init__(self, chunk_seconds: int = 900) -> None:
        self.chunk_seconds = chunk_seconds

    def extract_chunks(self, video_path: Path, output_dir: Path) -> list[AudioChunk]:
        self._require_binary("ffmpeg")
        self._require_binary("ffprobe")
        if not video_path.is_file():
            raise MediaProcessingError(f"Video file does not exist: {video_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = output_dir / "part_%03d.mp3"
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "64k",
            "-f",
            "segment",
            "-segment_time",
            str(self.chunk_seconds),
            "-reset_timestamps",
            "1",
            str(output_pattern),
        ]
        self._run(command, "Unable to extract audio from the video")

        paths = sorted(output_dir.glob("part_*.mp3"))
        if not paths:
            raise MediaProcessingError("FFmpeg produced no audio chunks")

        chunks: list[AudioChunk] = []
        offset = 0.0
        for index, path in enumerate(paths):
            duration = self._probe_duration(path)
            chunks.append(
                AudioChunk(
                    index=index,
                    path=path,
                    offset_seconds=offset,
                    duration_seconds=duration,
                )
            )
            offset += duration
        return chunks

    @staticmethod
    def _require_binary(name: str) -> None:
        if shutil.which(name) is None:
            raise MediaProcessingError(
                f"Required executable '{name}' was not found. Install FFmpeg first."
            )

    @staticmethod
    def _run(command: list[str], message: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            details = result.stderr.strip() or "unknown FFmpeg error"
            raise MediaProcessingError(f"{message}: {details}")
        return result

    def _probe_duration(self, path: Path) -> float:
        result = self._run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            f"Unable to inspect audio duration for {path.name}",
        )
        try:
            return float(result.stdout.strip())
        except ValueError as exc:
            raise MediaProcessingError(f"Invalid duration reported for {path.name}") from exc
