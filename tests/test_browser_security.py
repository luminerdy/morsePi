import unittest
from pathlib import Path

from flask import Flask, render_template_string
from browser_security import install_request_protection


class RequestProtectionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.template_folder = str(Path(__file__).resolve().parents[1] / "templates")
        install_request_protection(self.app)
        self.calls = []

        @self.app.route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        def action():
            from flask import request
            if request.method != "GET":
                self.calls.append(request.method)
            return render_template_string('{{ csrf_token() }}')

        self.client = self.app.test_client()

    def test_missing_forged_and_other_browser_tokens_block_all_writes(self):
        token = self.client.get("/").text
        other = self.app.test_client().get("/").text
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            for supplied in ("", "forged", other):
                response = self.client.open("/", method=method, headers={"X-CSRF-Token": supplied})
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.client.post("/", data={"csrf_token": token}).status_code, 200)
        self.assertEqual(self.client.post("/", json={}, headers={"X-CSRF-Token": token}).status_code, 200)

    def test_cookie_and_header_forgery_is_rejected(self):
        self.client.set_cookie("morse_browser_token", "forged")
        self.assertEqual(self.client.post("/", headers={"X-CSRF-Token": "forged"}).status_code, 403)
        self.assertFalse(self.calls)

    def test_html_is_not_cached_and_cookie_is_protected(self):
        response = self.client.get("/")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", response.headers["Set-Cookie"])

    def test_every_template_post_form_has_a_token(self):
        import re
        root = Path(__file__).resolve().parents[1] / "templates"
        for path in root.glob("*.html"):
            for form in re.findall(r'<form\b[^>]*method="post".*?</form>', path.read_text(encoding="utf-8"), re.S):
                self.assertIn('name="csrf_token"', form, path.name)
