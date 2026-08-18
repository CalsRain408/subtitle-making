import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from subtitle_maker.media.ffmpeg import FfmpegSubtitleRenderer


class FfmpegSubtitleRendererTest(TestCase):
    @patch(
        "subtitle_maker.media.ffmpeg.FfmpegSubtitleRenderer._find_subtitle_capable_ffmpeg",
        return_value="/usr/bin/ffmpeg",
    )
    @patch("subtitle_maker.media.ffmpeg.subprocess.run")
    def test_renderer_builds_compatible_mp4_command(
        self,
        run: object,
        _find_ffmpeg: object,
    ) -> None:
        with TemporaryDirectory() as directory:
            temp_path = Path(directory)
            video = temp_path / "input.mp4"
            subtitles = temp_path / "subtitles.ass"
            output = temp_path / "output.mp4"
            video.write_bytes(b"video")
            subtitles.write_text("subtitles", encoding="utf-8")

            def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                output.write_bytes(b"rendered")
                return subprocess.CompletedProcess(command, 0, "", "")

            run.side_effect = fake_run  # type: ignore[attr-defined]

            FfmpegSubtitleRenderer().render(video, subtitles, output)

            command = run.call_args.args[0]  # type: ignore[attr-defined]
            self.assertIn("subtitles=filename=", command[command.index("-vf") + 1])
            self.assertEqual(command[command.index("-c:v") + 1], "libx264")
            self.assertEqual(command[command.index("-pix_fmt") + 1], "yuv420p")
            self.assertEqual(output.read_bytes(), b"rendered")
