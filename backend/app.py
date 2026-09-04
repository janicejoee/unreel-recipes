import json

from flask import Flask, Response, g, jsonify, request, stream_with_context
from flask_cors import CORS
from supabase_auth.errors import AuthApiError

from auth import (
    auth_http_error,
    parse_email_password,
    refresh_session,
    require_user,
    sign_in,
    sign_up,
)
from recipe import iter_recipe_from_url
from store import get_recipe, list_recipes, public_recipe

app = Flask(__name__)
CORS(app)


@app.post("/auth/signup")
def signup():
    credentials, error = parse_email_password()
    if error:
        return error
    try:
        return jsonify(sign_up(credentials["email"], credentials["password"]))
    except (AuthApiError, RuntimeError) as exc:
        return auth_http_error(exc)


@app.post("/auth/login")
def login():
    credentials, error = parse_email_password()
    if error:
        return error
    try:
        return jsonify(sign_in(credentials["email"], credentials["password"]))
    except (AuthApiError, RuntimeError) as exc:
        return auth_http_error(exc)


@app.post("/auth/refresh")
def refresh():
    refresh_token = (request.get_json(silent=True) or {}).get("refresh_token", "").strip()
    if not refresh_token:
        return jsonify({"error": "Sign in to continue."}), 401
    try:
        return jsonify(refresh_session(refresh_token))
    except (AuthApiError, RuntimeError) as exc:
        return auth_http_error(exc)


@app.get("/auth/me")
@require_user
def me():
    return jsonify({"user": {"id": g.user.id, "email": g.user.email}})


@app.post("/extract")
@require_user
def extract():
    url = (request.get_json(silent=True) or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "Paste an Instagram reel URL."}), 400
    if "instagram.com" not in url:
        return jsonify({"error": "That doesn't look like an Instagram URL."}), 400

    user_id = g.user.id

    def generate():
        try:
            for event in iter_recipe_from_url(url, user_id):
                yield json.dumps(event) + "\n"
        except Exception as exc:
            yield json.dumps(
                {
                    "type": "error",
                    "error": str(exc) or "Could not extract a recipe from that reel.",
                }
            ) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/recipes")
@require_user
def recipes():
    return jsonify(list_recipes(g.user.id))


@app.get("/recipes/<recipe_id>")
@require_user
def recipe(recipe_id: str):
    record = public_recipe(get_recipe(recipe_id, g.user.id))
    if record is None:
        return jsonify({"error": "Recipe not found."}), 404
    return jsonify(record)


if __name__ == "__main__":
    app.run(debug=True, port=5050, threaded=True)
