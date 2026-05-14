from datetime import datetime, timezone
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com"


def _get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _tag_for_now() -> str:
    now = datetime.now(timezone.utc)
    return f"audio-{now.year}-{now.month:02d}"


def _find_or_create_release(repo: str, tag: str, token: str) -> dict:
    headers = _get_headers(token)

    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/releases/tags/{tag}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code != 404:
        resp.raise_for_status()

    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/releases",
        headers=headers,
        json={
            "tag_name": tag,
            "name": f"Audio — {tag}",
            "body": "Auto-generated monthly audio release for podcast feed.",
            "draft": False,
            "prerelease": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _delete_existing_asset(release: dict, filename: str, repo: str, token: str) -> None:
    headers = _get_headers(token)
    for asset in release.get("assets", []):
        if asset["name"] == filename:
            requests.delete(
                f"{GITHUB_API}/repos/{repo}/releases/assets/{asset['id']}",
                headers=headers,
                timeout=30,
            ).raise_for_status()
            return


def upload_audio(file_path: Path, repo: str, token: str) -> str:
    """
    Find or create the monthly GitHub Release, upload the MP3, and return
    the browser_download_url.
    """
    tag = _tag_for_now()
    release = _find_or_create_release(repo, tag, token)

    filename = file_path.name
    _delete_existing_asset(release, filename, repo, token)

    # Strip URI template suffix {?name,label} from upload_url
    upload_url = release["upload_url"].split("{")[0]

    headers = _get_headers(token)
    headers["Content-Type"] = "audio/mpeg"

    with file_path.open("rb") as fh:
        resp = requests.post(
            upload_url,
            headers=headers,
            params={"name": filename},
            data=fh,
            timeout=300,
        )
    resp.raise_for_status()
    return resp.json()["browser_download_url"]
