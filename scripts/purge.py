#!/usr/bin/env python3
"""
Nightly purge of expired episodes.
Reads RETENTION_DAYS from env (default 14).
Deletes release assets, chapters JSON files, removes from episodes.json, rebuilds feed.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from feed import rebuild_feed  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
EPISODES_PATH = REPO_ROOT / "data" / "episodes.json"
FEED_PATH = REPO_ROOT / "feed" / "feed.xml"
GITHUB_API = "https://api.github.com"


def _get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _delete_release_asset(repo: str, download_url: str, token: str) -> None:
    try:
        # download_url pattern: .../releases/download/{tag}/{filename}
        after_download = download_url.split("/releases/download/")[1]
        tag, filename = after_download.split("/", 1)
    except (IndexError, ValueError):
        print(f"[purge] Could not parse download URL: {download_url}")
        return

    headers = _get_headers(token)
    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 404:
        print(f"[purge] Release {tag} not found, skipping asset deletion.")
        return
    if resp.status_code != 200:
        print(f"[purge] Warning: could not fetch release {tag}: {resp.status_code}")
        return

    release = resp.json()
    for asset in release.get("assets", []):
        if asset["name"] == filename:
            del_resp = requests.delete(
                f"{GITHUB_API}/repos/{repo}/releases/assets/{asset['id']}",
                headers=headers,
                timeout=30,
            )
            if del_resp.status_code == 204:
                print(f"[purge] Deleted release asset: {filename}")
            else:
                print(f"[purge] Warning: could not delete {filename}: {del_resp.status_code}")
            return
    print(f"[purge] Asset {filename} not found in release {tag} (already deleted?).")


def _delete_chapters_file(video_id: str) -> None:
    chapters_path = REPO_ROOT / "feed" / "chapters" / f"{video_id}.json"
    if chapters_path.exists():
        chapters_path.unlink()
        print(f"[purge] Deleted chapters file: {chapters_path.name}")


def _build_feed_config(repo: str) -> dict:
    owner, repo_name = repo.split("/", 1)
    default_image = f"https://{owner}.github.io/{repo_name}/feed/cover.png"
    return {
        "title": os.environ.get("FEED_TITLE", f"{owner}'s YouTube Podcast"),
        "description": os.environ.get(
            "FEED_DESC", "Auto-generated audio podcast from curated YouTube videos"
        ),
        "link": f"https://{owner}.github.io/{repo_name}/feed/feed.xml",
        "author": owner,
        "language": "en",
        "image_url": os.environ.get("FEED_IMAGE_URL", default_image),
    }


def main():
    token = os.environ["GH_TOKEN"]
    repo = os.environ["REPO"]
    retention_days = int(os.environ.get("RETENTION_DAYS", "14"))

    if not EPISODES_PATH.exists():
        print("[purge] No episodes.json found. Nothing to purge.")
        return

    episodes = json.loads(EPISODES_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    kept = []
    purged_count = 0

    for ep in episodes:
        expires_at_str = ep.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        else:
            ripped = datetime.fromisoformat(ep["ripped_at"].replace("Z", "+00:00"))
            expires_at = ripped + timedelta(days=retention_days)

        if now >= expires_at:
            print(f"[purge] Expiring: {ep['title']!r} (expired {expires_at.date()})")
            _delete_release_asset(repo, ep["download_url"], token)
            _delete_chapters_file(ep["video_id"])
            purged_count += 1
        else:
            kept.append(ep)

    if purged_count == 0:
        print("[purge] No expired episodes found.")
        return

    tmp = EPISODES_PATH.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(kept, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp, EPISODES_PATH)
    print(f"[purge] Purged {purged_count} episode(s). {len(kept)} remaining.")

    rebuild_feed(EPISODES_PATH, FEED_PATH, _build_feed_config(repo))
    print("[purge] Feed rebuilt.")


if __name__ == "__main__":
    main()
