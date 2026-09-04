import json
import os
import tempfile

import anthropic

from fetch import fetch_instagram_audio, fetch_instagram_meta
from store import save_recipe
from transcribe import transcribe_audio

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_recipe(caption: str, transcript: str | None = None) -> dict:
    prompt = f"""Extract a structured recipe from this Instagram post.

    Caption:
    {caption}

    {"Spoken transcript from the video:\n" + transcript if transcript else ""}

    Return ONLY valid JSON, no other text:
    {{"title": "string", "ingredients": [{{"name": "string", "quantity": "string", "unit": "string"}}], "steps": ["string"]}}
    
    Only include ingredients and steps that are explicitly mentioned in the caption or transcript. Do not make up any ingredients or steps.
    Do not return result with ```json or ```.
    """

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    return json.loads(response.content[0].text)


def iter_recipe_from_url(url: str, user_id: str):
    yield {"type": "status", "message": "Unreeling the recipe…"}
    meta = fetch_instagram_meta(url)

    result = extract_recipe(caption=meta["caption"])

    if not result.get("ingredients") or not result.get("steps"):
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = fetch_instagram_audio(url, tmp)
            transcript = transcribe_audio(audio_path)
        result = extract_recipe(caption=meta["caption"], transcript=transcript)

    yield {"type": "status", "message": "Saving the recipe…"}
    record = save_recipe(
        result,
        source=url,
        user_id=user_id,
        thumbnail=meta.get("thumbnail"),
        thumbnail_type=meta.get("thumbnail_type") or "image/jpeg",
    )
    yield {"type": "recipe", "recipe": record}
