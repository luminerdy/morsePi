"""Browser request tokens, bound to a signed browser cookie."""
import hmac
import secrets

from flask import g, jsonify, render_template, request
from itsdangerous import BadSignature, URLSafeSerializer


def install_request_protection(app):
    signer = URLSafeSerializer(secrets.token_hex(32), salt="morsepi-csrf")
    cookie_name = "morse_browser_token"

    def token():
        if not hasattr(g, "csrf_token"):
            supplied = request.cookies.get(cookie_name, "")
            try:
                valid = isinstance(signer.loads(supplied), str)
            except BadSignature:
                valid = False
            g.csrf_token = supplied if valid else signer.dumps(secrets.token_hex(32))
        return g.csrf_token

    @app.before_request
    def protect_request():
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        expected = token()
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not hmac.compare_digest(expected.encode(), supplied.encode()):
            if request.headers.get("X-CSRF-Token") or request.is_json:
                return jsonify(error="csrf", message="Page expired. Reload and try again."), 403
            return render_template("request_expired.html"), 403

    @app.context_processor
    def token_context():
        return {"csrf_token": token}

    @app.after_request
    def persist_token(response):
        if response.mimetype == "text/html":
            response.set_cookie(cookie_name, token(), httponly=True, samesite="Strict")
            response.headers["Cache-Control"] = "no-store"
        return response

