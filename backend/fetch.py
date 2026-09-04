import tempfile
from pathlib import Path

import yt_dlp

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _read_thumbnail(tmp: Path, info: dict, ydl: yt_dlp.YoutubeDL) -> tuple[bytes | None, str]:
    for path in tmp.iterdir():
        content_type = IMAGE_TYPES.get(path.suffix.lower())
        if content_type:
            return path.read_bytes(), content_type

    thumbnail_url = info.get("thumbnail")
    if not thumbnail_url:
        return None, "image/jpeg"
    try:
        with ydl.urlopen(thumbnail_url) as response:
            return response.read(), "image/jpeg"
    except Exception:
        return None, "image/jpeg"


def fetch_instagram_meta(url: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "writethumbnail": True,
            "outtmpl": str(output / "%(id)s.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            thumbnail, thumbnail_type = _read_thumbnail(output, info, ydl)

    return {
        "caption": info.get("description", "") or "",
        "thumbnail": thumbnail,
        "thumbnail_type": thumbnail_type,
    }


def fetch_instagram_audio(url: str, output_dir: str) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    ydl_opts = {
        "outtmpl": str(output / "%(id)s.%(ext)s"),
        "quiet": True,
        "format": "bestaudio/best",
        "keepvideo": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_path = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
    if not audio_path.exists():
        raise RuntimeError("Could not extract audio from that reel.")
    return str(audio_path)
