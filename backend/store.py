import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent / ".env")

_client = None
PUBLIC_FIELDS = (
    "id",
    "source",
    "created_at",
    "title",
    "ingredients",
    "steps",
    "thumbnail_url",
)


def supabase_client():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env."
            )
        _client = create_client(url, key)
    return _client


def instagram_id_from_url(url: str) -> str:
    match = re.search(r"instagram\.com/(?:reel|reels|p)/([^/?#]+)", url)
    if match:
        return match.group(1)
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", url)[-40:]


def public_recipe(row: dict | None) -> dict | None:
    if not row:
        return None
    return {key: row.get(key) for key in PUBLIC_FIELDS}


def list_recipes(user_id: str) -> list[dict]:
    response = (
        supabase_client()
        .table("recipes")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [public_recipe(row) for row in (response.data or [])]


def get_recipe(recipe_id: str, user_id: str) -> dict | None:
    response = (
        supabase_client()
        .table("recipes")
        .select("*")
        .eq("id", recipe_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


THUMB_BUCKET = "thumbnails"
THUMB_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def upload_thumbnail(user_id: str, recipe_id: str, data: bytes, content_type: str) -> str:
    ext = THUMB_EXT.get(content_type, "jpg")
    path = f"{user_id}/{recipe_id}.{ext}"
    bucket = supabase_client().storage.from_(THUMB_BUCKET)
    bucket.upload(
        path,
        data,
        {
            "content-type": content_type,
            "upsert": "true",
            "cache-control": "31536000",
        },
    )
    return bucket.get_public_url(path)


def save_recipe(
    recipe: dict,
    source: str,
    user_id: str,
    thumbnail: bytes | None = None,
    thumbnail_type: str = "image/jpeg",
) -> dict:
    recipe_id = instagram_id_from_url(source)
    existing = get_recipe(recipe_id, user_id) or {}
    thumbnail_url = existing.get("thumbnail_url")
    if thumbnail:
        thumbnail_url = upload_thumbnail(user_id, recipe_id, thumbnail, thumbnail_type)
    record = {
        "id": recipe_id,
        "user_id": user_id,
        "source": source,
        "created_at": existing.get("created_at")
        or datetime.now(timezone.utc).isoformat(),
        "title": recipe.get("title") or "Untitled recipe",
        "ingredients": recipe.get("ingredients") or [],
        "steps": recipe.get("steps") or [],
        "thumbnail_url": thumbnail_url,
    }
    supabase_client().table("recipes").upsert(
        record, on_conflict="user_id,id"
    ).execute()
    return public_recipe(record)
