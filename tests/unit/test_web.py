from unittest import TestCase

from fastapi.testclient import TestClient

from subtitle_maker.api.app import app


class WebAppTest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_homepage_is_served(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Subtitle Maker", response.text)
        self.assertIn("创建字幕任务", response.text)

    def test_web_assets_are_served(self) -> None:
        stylesheet = self.client.get("/static/styles.css")
        script = self.client.get("/static/app.js")

        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("--green", stylesheet.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("XMLHttpRequest", script.text)
