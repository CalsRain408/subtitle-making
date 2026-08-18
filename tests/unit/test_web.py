from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from subtitle_maker.api.app import app
from subtitle_maker.jobs.store import FileJobStore


class WebAppTest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_homepage_is_served(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Subtitle Maker", response.text)
        self.assertIn("创建字幕任务", response.text)
        self.assertIn("下载字幕成片", response.text)

    def test_web_assets_are_served(self) -> None:
        stylesheet = self.client.get("/static/styles.css")
        script = self.client.get("/static/app.js")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("--green", stylesheet.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("XMLHttpRequest", script.text)

    def test_rendered_video_can_be_downloaded(self) -> None:
        with TemporaryDirectory() as directory:
            store = FileJobStore(Path(directory))
            record = store.create("episode.mov").mark_succeeded(12)
            store.save(record)
            store.video_output_path(record.id).write_bytes(b"rendered mp4")

            with patch("subtitle_maker.api.app.store", store):
                response = self.client.get(f"/v1/jobs/{record.id}/video")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "video/mp4")
            self.assertIn("episode.bilingual.mp4", response.headers["content-disposition"])
            self.assertEqual(response.content, b"rendered mp4")
