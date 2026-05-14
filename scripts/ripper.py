import json
import os
import subprocess
from pathlib import Path

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 "
    "Mobile/15E148 Safari/604.1"
)
PLAYER_CLIENTS = "youtube:player_client=mweb,web_safari,default,tv_simply"


def _cookies_args() -> list[str]:
    path = os.environ.get("YT_COOKIES_FILE", "")
    if path and Path(path).exists():
        return ["--cookies", path]
    return []


def _common_args() -> list[str]:
    return [
        "--extractor-args", PLAYER_CLIENTS,
        "--user-agent", MOBILE_UA,
        "--retries", "5",
        "--extractor-retries", "5",
        "--sleep-requests", "1",
    ]


def fetch_metadata(url: str) -> dict:
    """
    Run yt-dlp --dump-json with no download.
    Raises RuntimeError with a human-readable message on failure.
    """
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        *_common_args(),
        *_cookies_args(),
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _raise_descriptive_error(result.stderr.strip(), url)
    return json.loads(result.stdout)


def rip(url: str, output_dir: Path) -> dict:
    """
    Download and extract audio to output_dir/{video_id}.mp3.
    Returns episode metadata dict.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = fetch_metadata(url)
    video_id = meta["id"]
    output_template = str(output_dir / f"{video_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-playlist",
        *_common_args(),
        *_cookies_args(),
        "--output", output_template,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _raise_descriptive_error(result.stderr.strip(), url)

    file_path = output_dir / f"{video_id}.mp3"
    if not file_path.exists():
        raise FileNotFoundError(
            f"yt-dlp exited 0 but {file_path} was not created.\n"
            f"stdout tail: {result.stdout[-500:]}"
        )

    return {
        "video_id": video_id,
        "title": meta.get("title", ""),
        "channel": meta.get("uploader") or meta.get("channel", ""),
        "description": meta.get("description", ""),
        "upload_date": meta.get("upload_date", ""),
        "duration_seconds": int(meta.get("duration") or 0),
        "thumbnail_url": meta.get("thumbnail", ""),
        "original_url": url,
        "file_path": str(file_path),
        "file_size_bytes": file_path.stat().st_size,
        "chapters": meta.get("chapters") or [],
    }


def _raise_descriptive_error(stderr: str, url: str) -> None:
    lower = stderr.lower()
    if "members only" in lower or "member-only" in lower:
        raise RuntimeError(f"Video is members-only and cannot be downloaded: {url}")
    if "age" in lower and ("restrict" in lower or "confirm" in lower):
        raise RuntimeError(f"Video is age-restricted and requires authentication: {url}")
    if "private video" in lower:
        raise RuntimeError(f"Video is private: {url}")
    if "video unavailable" in lower or "has been removed" in lower:
        raise RuntimeError(f"Video is unavailable or has been removed: {url}")
    if "sign in" in lower or "login" in lower:
        raise RuntimeError(
            f"Video requires sign-in: {url}\nyt-dlp error: {stderr}"
        )
    raise RuntimeError(f"yt-dlp failed for {url}:\n{stderr}")
