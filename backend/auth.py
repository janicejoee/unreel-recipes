import os
import re
from functools import wraps

from flask import g, jsonify, request
from supabase import create_client
from supabase_auth.errors import AuthApiError

from store import supabase_client

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _supabase_settings() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )
    return url, key


def _auth_client():
    url, key = _supabase_settings()
    return create_client(url, key)


def _user_payload(user) -> dict:
    return {"id": user.id, "email": user.email}


def session_payload(response) -> dict:
    if not response.session or not response.user:
        raise RuntimeError("Could not start a session.")
    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
        "user": _user_payload(response.user),
    }


def parse_email_password():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not EMAIL_RE.match(email):
        return None, (jsonify({"error": "Enter a valid email address."}), 400)
    if len(password) < 6:
        return None, (
            jsonify({"error": "Password must be at least 6 characters."}),
            400,
        )
    return {"email": email, "password": password}, None


def auth_http_error(exc: Exception):
    if isinstance(exc, AuthApiError):
        message = exc.message or "Authentication failed."
        lowered = message.lower()
        if "already" in lowered and "register" in lowered:
            return jsonify({"error": "An account with that email already exists."}), 409
        if "invalid" in lowered or "credentials" in lowered:
            return jsonify({"error": "Incorrect email or password."}), 401
        status = exc.status if exc.status and exc.status >= 400 else 400
        return jsonify({"error": message}), status
    return jsonify({"error": str(exc) or "Authentication failed."}), 400


def sign_up(email: str, password: str) -> dict:
    supabase_client().auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
        }
    )
    return sign_in(email, password)


def sign_in(email: str, password: str) -> dict:
    response = _auth_client().auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    return session_payload(response)


def refresh_session(refresh_token: str) -> dict:
    response = _auth_client().auth.refresh_session(refresh_token)
    return session_payload(response)


def user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        response = supabase_client().auth.get_user(token)
    except AuthApiError:
        return None
    return response.user if response else None


def require_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = user_from_request()
        if not user:
            return jsonify({"error": "Sign in to continue."}), 401
        g.user = user
        return fn(*args, **kwargs)

    return wrapper
