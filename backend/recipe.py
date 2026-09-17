import json
import os
import tempfile

import anthropic

from fetch import fetch_instagram_audio, fetch_instagram_meta, fetch_website_page
from store import save_recipe
from transcribe import transcribe_audio

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_recipe(content: str) -> dict:
    prompt = f"""Extract a structured recipe from this content.

    {content}

    Return ONLY valid JSON, no other text:
    {{"title": "string", "ingredients": [{{"name": "string", "quantity": "string", "unit": "string"}}], "steps": ["string"]}}

    Only include ingredients and steps that are explicitly mentioned. Do not make up any ingredients or steps.
    Do not return result with ```json or ```.
    """

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    return json.loads(response.content[0].text)


def _instagram_content(caption: str, transcript: str | None = None) -> str:
    parts = [f"Caption:\n{caption}"]
    if transcript:
        parts.append(f"Spoken transcript from the video:\n{transcript}")
    return "\n\n".join(parts)


def _website_content(structured: dict | None, page_text: str) -> str:
    if structured:
        return "Structured recipe data from the page:\n" + json.dumps(
            structured, ensure_ascii=False
        )[:8000]
    if page_text.strip():
        return f"Page text:\n{page_text}"
    raise RuntimeError("Could not find a recipe on that page.")


def _save(result: dict, url: str, user_id: str, source_type: str, meta: dict):
    return save_recipe(
        result,
        source=url,
        user_id=user_id,
        source_type=source_type,
        thumbnail=meta.get("thumbnail"),
        thumbnail_type=meta.get("thumbnail_type") or "image/jpeg",
    )


def _iter_instagram_recipe(url: str, user_id: str):
    yield {"type": "status", "message": "Unreeling the recipe…"}
    meta = fetch_instagram_meta(url)

    result = extract_recipe(_instagram_content(meta["caption"]))

    if not result.get("ingredients") or not result.get("steps"):
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = fetch_instagram_audio(url, tmp)
            transcript = transcribe_audio(audio_path)
        result = extract_recipe(_instagram_content(meta["caption"], transcript))

    yield {"type": "status", "message": "Saving the recipe…"}
    record = _save(result, url, user_id, "instagram", meta)
    yield {"type": "recipe", "recipe": record}


def _iter_website_recipe(url: str, user_id: str):
    yield {"type": "status", "message": "Reading the recipe…"}
    page = fetch_website_page(url)
    result = extract_recipe(_website_content(page["structured_recipe"], page["page_text"]))
    if not result.get("ingredients") or not result.get("steps"):
        raise RuntimeError("Could not extract a recipe from that page.")

    yield {"type": "status", "message": "Saving the recipe…"}
    record = _save(result, url, user_id, "website", page)
    yield {"type": "recipe", "recipe": record}


def iter_recipe_from_url(url: str, user_id: str, source_type: str = "instagram"):
    if source_type == "website":
        yield from _iter_website_recipe(url, user_id)
        return
    yield from _iter_instagram_recipe(url, user_id)
