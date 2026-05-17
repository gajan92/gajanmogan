#!/usr/bin/env python3
"""
CLI entrypoint for the GitHub Actions workflow.

Usage:
    python scripts/process_url.py \\
        --url <youtube_url> \\
        --issue-number <int> \\
        --repo <owner/repo>

Environment:
    GH_TOKEN        GitHub token with issues + contents + releases scope
    RETENTION_DAYS  Days before episode expires (default: 14)
    FEED_TITLE      Override feed channel title
    FEED_DESC       Override feed channel description
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from filter import is_visual_heavy  # noqa: E402
from ripper import fetch_metadata, rip  # noqa: E402
from release import upload_audio  # noqa: E402
from feed import rebuild_feed  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
EPISODES_PATH = REPO_ROOT / "data" / "episodes.json"
FEED_PATH = REPO_ROOT / "feed" / "feed.xml"
AUDIO_DIR = REPO_ROOT / "audio"

GH_API = "https://api.github.com"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_comment(issue_number: int, body: str, repo: str, token: str) -> None:
    resp = requests.post(
        f"{GH_API}/repos/{repo}/issues/{issue_number}/comments",
        headers=_gh_headers(token),
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()


def gh_close_with_label(issue_number: int, label: str, repo: str, token: str) -> None:
    base = f"{GH_API}/repos/{repo}"
    headers = _gh_headers(token)

    # Create label if it doesn't exist (422 = already exists — that's fine)
    requests.post(
        f"{base}/labels",
        headers=headers,
        json={"name": label, "color": "ededed"},
        timeout=30,
    )

    requests.post(
        f"{base}/issues/{issue_number}/labels",
        headers=headers,
        json={"labels": [label]},
        timeout=30,
    ).raise_for_status()

    requests.patch(
        f"{base}/issues/{issue_number}",
        headers=headers,
        json={"state": "closed"},
        timeout=30,
    ).raise_for_status()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_episodes() -> list:
    if not EPISODES_PATH.exists():
        return []
    return json.loads(EPISODES_PATH.read_text(encoding="utf-8"))


def _save_episodes(episodes: list) -> None:
    EPISODES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EPISODES_PATH.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(episodes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp, EPISODES_PATH)


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


def _normalize_date(yt_date: str) -> str:
    """'20260514' -> '2026-05-14'. Pass through if already hyphenated."""
    d = yt_date.replace("-", "")
    if len(d) == 8 and d.isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return yt_date


def _format_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def _chapters_url(repo: str, video_id: str) -> str:
    owner, repo_name = repo.split("/", 1)
    return f"https://{owner}.github.io/{repo_name}/feed/chapters/{video_id}.json"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--issue-number", required=True, type=int)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    token = os.environ["GH_TOKEN"]

    try:
        # Step 1: Fetch metadata (fast, no download)
        meta = fetch_metadata(args.url)

        # Step 2: Filter check
        is_heavy, reason = is_visual_heavy(
            title=meta.get("title", ""),
            description=meta.get("description", ""),
            channel=meta.get("uploader") or meta.get("channel", ""),
        )
        if is_heavy:
            gh_comment(
                args.issue_number,
                f"Skipping: video appears to be visual-heavy ({reason}).\n\n"
                f"To override, add the channel name to `data/allowlist.txt` and reopen this issue.",
                args.repo,
                token,
            )
            gh_close_with_label(args.issue_number, "skipped", args.repo, token)
            sys.exit(0)

        # Step 3: Rip audio (reuse metadata to avoid a second yt-dlp call)
        rip_result = rip(args.url, AUDIO_DIR, meta=meta)

        # Step 4: Upload to GitHub Release
        download_url = upload_audio(Path(rip_result["file_path"]), args.repo, token)

        # Step 5: Build episode record
        now = datetime.now(timezone.utc)
        retention_days = int(os.environ.get("RETENTION_DAYS", "14"))
        chapters = rip_result.get("chapters") or []
        chapters_url = _chapters_url(args.repo, rip_result["video_id"]) if chapters else ""

        episode = {
            "video_id": rip_result["video_id"],
            "title": rip_result["title"],
            "channel": rip_result["channel"],
            "description": rip_result["description"],
            "upload_date": _normalize_date(rip_result["upload_date"]),
            "duration_seconds": rip_result["duration_seconds"],
            "thumbnail_url": rip_result["thumbnail_url"],
            "original_url": rip_result["original_url"],
            "download_url": download_url,
            "file_size_bytes": rip_result["file_size_bytes"],
            "chapters": chapters,
            "chapters_url": chapters_url,
            "view_count": rip_result.get("view_count"),
            "like_count": rip_result.get("like_count"),
            "comment_count": rip_result.get("comment_count"),
            "ripped_at": now.isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(days=retention_days))
                          .isoformat().replace("+00:00", "Z"),
            "issue_number": args.issue_number,
        }

        # Step 6: Append to episodes.json (deduplicate by video_id)
        episodes = _load_episodes()
        episodes = [e for e in episodes if e["video_id"] != episode["video_id"]]
        episodes.append(episode)
        _save_episodes(episodes)

        # Step 7: Rebuild RSS feed (also writes chapters JSON if applicable)
        rebuild_feed(EPISODES_PATH, FEED_PATH, _build_feed_config(args.repo))

        # Step 8: Comment success and close issue
        duration_str = _format_duration(rip_result["duration_seconds"])
        chapters_note = f"\nChapters: {chapters_url}" if chapters_url else ""
        gh_comment(
            args.issue_number,
            f"✅ Added: **{rip_result['title']}** ({duration_str})\n\n"
            f"Download: {download_url}{chapters_note}\n"
            f"Expires: {episode['expires_at'][:10]}",
            args.repo,
            token,
        )
        gh_close_with_label(args.issue_number, "processed", args.repo, token)

    except Exception:
        tb = traceback.format_exc()
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            try:
                with open(summary_path, "a") as f:
                    f.write(f"## Processing failed\n\n```\n{tb}\n```\n")
            except Exception:
                pass
        try:
            gh_comment(
                args.issue_number,
                f"Processing failed. The issue will remain open for retry.\n\n"
                f"```\n{tb}\n```",
                args.repo,
                token,
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
