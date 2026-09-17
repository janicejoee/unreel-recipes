import ipaddress
import json
import socket
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import yt_dlp

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

IMAGE_CONTENT_TYPES = set(IMAGE_TYPES.values())
MAX_HTML_BYTES = 2_000_000
MAX_IMAGE_BYTES = 1_000_000
MAX_PAGE_TEXT_CHARS = 12_000
REQUEST_TIMEOUT = 20.0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

RECIPE_FIELDS = (
    "name",
    "headline",
    "description",
    "recipeIngredient",
    "ingredients",
    "recipeInstructions",
    "instructions",
)


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


def assert_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RuntimeError("Paste a valid http or https URL.")
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("That URL isn't allowed.")
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise RuntimeError("Could not reach that website.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise RuntimeError("That URL isn't allowed.")


def _http_get(url: str, *, max_bytes: int, accept: str) -> tuple[bytes, str, str]:
    assert_public_http_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            final_url = response.geturl()
            assert_public_http_url(final_url)
            content = response.read(max_bytes)
            content_type = response.headers.get("Content-Type") or ""
    except HTTPError as exc:
        raise RuntimeError("Could not load that website.") from exc
    except URLError as exc:
        raise RuntimeError("Could not load that website.") from exc
    return content, final_url, content_type


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _is_recipe_type(type_value) -> bool:
    for item in _as_list(type_value):
        if isinstance(item, str) and item.split("/")[-1] == "Recipe":
            return True
    return False


def _collect_recipes(node, found: list) -> None:
    if isinstance(node, list):
        for item in node:
            _collect_recipes(item, found)
        return
    if not isinstance(node, dict):
        return
    if _is_recipe_type(node.get("@type")):
        found.append(node)
        return
    graph = node.get("@graph")
    if graph is not None:
        _collect_recipes(graph, found)
        return
    for key in ("mainEntity", "mainEntityOfPage"):
        if key in node:
            _collect_recipes(node[key], found)


def _slim_recipe(recipe: dict) -> dict:
    slim = {key: recipe[key] for key in RECIPE_FIELDS if key in recipe}
    return slim or recipe


class _PageParser(HTMLParser):
    skip_tags = {"script", "style", "noscript", "nav", "footer", "header", "iframe"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_ld: list[str] = []
        self.og_image: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0
        self._in_json_ld = False
        self._json_ld_buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = {key.lower(): value for key, value in attrs if value is not None}
        if tag in self.skip_tags:
            self._skip_depth += 1
        if tag == "script" and "ld+json" in attrs_d.get("type", "").lower():
            self._in_json_ld = True
            self._json_ld_buf = []
        if tag == "meta":
            prop = (attrs_d.get("property") or attrs_d.get("name") or "").lower()
            if prop == "og:image":
                content = (attrs_d.get("content") or "").strip()
                if content:
                    self.og_image = content

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_ld_buf))
            self._in_json_ld = False
            self._json_ld_buf = []
        if tag in self.skip_tags and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_ld_buf.append(data)
        elif self._skip_depth == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def page_text(self) -> str:
        return " ".join(self._parts)[:MAX_PAGE_TEXT_CHARS]


def _parse_page(html: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return parser


def _parse_json_ld_recipes(blocks: list[str]) -> list[dict]:
    recipes = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        _collect_recipes(data, recipes)
    return recipes


def _image_url_from_recipe(recipe: dict) -> str | None:
    image = recipe.get("image")
    if isinstance(image, str) and image.strip():
        return image.strip()
    if isinstance(image, list) and image:
        return _image_url_from_recipe({"image": image[0]})
    if isinstance(image, dict):
        for key in ("url", "contentUrl"):
            value = image.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list) and value and isinstance(value[0], str):
                return value[0].strip()
    return None


def _fetch_image(url: str) -> tuple[bytes | None, str]:
    try:
        content, _, content_type_header = _http_get(
            url,
            max_bytes=MAX_IMAGE_BYTES,
            accept="image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        )
    except Exception:
        return None, "image/jpeg"
    content_type = (content_type_header or "image/jpeg").split(";")[0].strip()
    if content_type not in IMAGE_CONTENT_TYPES:
        suffix = Path(urlparse(url).path).suffix.lower()
        content_type = IMAGE_TYPES.get(suffix, "image/jpeg")
    return content or None, content_type


def fetch_website_page(url: str) -> dict:
    content, final_url, _ = _http_get(
        url,
        max_bytes=MAX_HTML_BYTES,
        accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    )
    html = content.decode("utf-8", errors="replace")
    page = _parse_page(html)
    recipes = _parse_json_ld_recipes(page.json_ld)
    raw_recipe = recipes[0] if recipes else None
    structured = _slim_recipe(raw_recipe) if raw_recipe else None
    image_url = _image_url_from_recipe(raw_recipe) if raw_recipe else None
    if not image_url:
        image_url = page.og_image
    thumbnail = None
    thumbnail_type = "image/jpeg"
    if image_url:
        thumbnail, thumbnail_type = _fetch_image(urljoin(final_url, image_url))
    return {
        "structured_recipe": structured,
        "page_text": page.page_text(),
        "thumbnail": thumbnail,
        "thumbnail_type": thumbnail_type,
    }
