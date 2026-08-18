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
        ffmpeg_binary = self._require_binary("ffmpeg")
        self._require_binary("ffprobe")
        if not video_path.is_file():
            raise MediaProcessingError(f"Video file does not exist: {video_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = output_dir / "part_%03d.mp3"
        command = [
            ffmpeg_binary,
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
    def _require_binary(name: str) -> str:
        found = shutil.which(name)
        if found is not None:
            return found
        full_prefixes = (
            Path("/opt/homebrew/opt/ffmpeg-full/bin"),
            Path("/usr/local/opt/ffmpeg-full/bin"),
        )
        for prefix in full_prefixes:
            candidate = prefix / name
            if candidate.is_file():
                return str(candidate)
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
                self._require_binary("ffprobe"),
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


class FfmpegSubtitleRenderer:
    """Burns an ASS subtitle track into an MP4 video."""

    def render(self, video_path: Path, subtitle_path: Path, output_path: Path) -> None:
        ffmpeg_binary = self._find_subtitle_capable_ffmpeg()
        if not video_path.is_file():
            raise MediaProcessingError(f"Video file does not exist: {video_path}")
        if not subtitle_path.is_file():
            raise MediaProcessingError(f"Subtitle file does not exist: {subtitle_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        escaped_subtitle_path = self._escape_filter_path(subtitle_path.resolve())
        subtitle_filter = f"subtitles=filename='{escaped_subtitle_path}'"
        command = [
            ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            subtitle_filter,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map_metadata",
            "0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        FfmpegAudioExtractor._run(command, "Unable to render subtitles into the video")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise MediaProcessingError("FFmpeg produced no rendered video")

    @staticmethod
    def _escape_filter_path(path: Path) -> str:
        return str(path).replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")

    @classmethod
    def _find_subtitle_capable_ffmpeg(cls) -> str:
        candidates = [
            Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"),
            Path("/usr/local/opt/ffmpeg-full/bin/ffmpeg"),
        ]
        path_binary = shutil.which("ffmpeg")
        if path_binary is not None:
            candidates.append(Path(path_binary))

        for candidate in candidates:
            if candidate.is_file() and cls._supports_subtitles_filter(str(candidate)):
                return str(candidate)
        raise MediaProcessingError(
            "FFmpeg does not include the libass subtitles filter. "
            "On macOS install it with 'brew install ffmpeg-full'."
        )

    @staticmethod
    def _supports_subtitles_filter(binary: str) -> bool:
        result = subprocess.run(
            [binary, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return any(
            len(fields) > 1 and fields[1] == "subtitles"
            for fields in (line.split() for line in result.stdout.splitlines())
        )
