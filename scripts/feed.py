import html
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator

PODCAST_NS = "https://podcastindex.org/namespace/1.0"


def _sanitize_description(text: str, max_chars: int = 4000) -> str:
    cleaned = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cc", "Cf") or ch in ("\t", "\n", "\r")
    )
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "…"
    return html.escape(cleaned, quote=False)


def _format_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%-d %B %Y")
    except ValueError:
        return date_str


def _format_count(n) -> str:
    if n is None:
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _parse_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _write_chapters_file(chapters: list, video_id: str, feed_dir: Path) -> None:
    chapters_dir = feed_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.2.0",
        "chapters": [
            {"startTime": int(ch.get("start_time", 0)), "title": ch.get("title", "")}
            for ch in chapters
        ],
    }
    (chapters_dir / f"{video_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def rebuild_feed(episodes_json_path: Path, output_path: Path, config: dict) -> None:
    """
    Read episodes.json, build RSS 2.0 + iTunes + Podcasting 2.0 feed,
    write chapters JSON files for episodes that have them, and write feed.xml.

    config keys: title, description, link, author, language, image_url (optional)
    """
    episodes = json.loads(episodes_json_path.read_text(encoding="utf-8"))

    fg = FeedGenerator()
    fg.load_extension("podcast")

    fg.title(config["title"])
    fg.description(config["description"])
    fg.link(href=config["link"], rel="alternate")
    fg.language(config.get("language", "en"))
    fg.author({"name": config["author"]})
    fg.podcast.itunes_author(config["author"])
    fg.podcast.itunes_explicit("no")

    if config.get("image_url"):
        fg.image(config["image_url"])
        fg.podcast.itunes_image(config["image_url"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    feed_dir = output_path.parent

    sorted_episodes = sorted(
        episodes,
        key=lambda e: e.get("ripped_at", ""),
        reverse=True,
    )

    for ep in sorted_episodes:
        fe = fg.add_entry()
        fe.id(ep["video_id"])
        fe.title(ep["title"])

        original_url = ep.get("original_url", "")

        meta_parts = []
        if ep.get("channel"):
            meta_parts.append(f"Channel: {ep['channel']}")
        if ep.get("upload_date"):
            meta_parts.append(f"Uploaded: {_format_date(ep['upload_date'])}")
        if ep.get("view_count") is not None:
            meta_parts.append(f"Views: {_format_count(ep['view_count'])}")
        if ep.get("like_count") is not None:
            meta_parts.append(f"Likes: {_format_count(ep['like_count'])}")
        if ep.get("comment_count") is not None:
            meta_parts.append(f"Comments: {_format_count(ep['comment_count'])}")

        description = _sanitize_description(ep.get("description", ""))
        if meta_parts:
            description = "\n".join(meta_parts) + "\n\n" + description
        if original_url:
            description += f"\n\nWatch on YouTube: {original_url}"
        fe.description(description)

        pub = datetime.fromisoformat(ep["ripped_at"].replace("Z", "+00:00"))
        fe.pubDate(pub)

        fe.enclosure(
            url=ep["download_url"],
            length=str(ep["file_size_bytes"]),
            type="audio/mpeg",
        )

        fe.podcast.itunes_duration(_parse_duration(ep["duration_seconds"]))
        fe.podcast.itunes_explicit("no")

        thumbnail_url = ep.get("thumbnail_url", "")
        if thumbnail_url:
            base = thumbnail_url.split("?")[0].lower()
            if base.endswith(".webp"):
                # Fix both the path segment and extension for YouTube webp URLs
                thumbnail_url = thumbnail_url.replace("vi_webp/", "vi/")
                thumbnail_url = thumbnail_url[:thumbnail_url.lower().rfind(".webp")] + ".jpg"
            if thumbnail_url.split("?")[0].lower().endswith((".jpg", ".png")):
                fe.podcast.itunes_image(thumbnail_url)

        chapters = ep.get("chapters") or []
        if chapters:
            _write_chapters_file(chapters, ep["video_id"], feed_dir)

    raw_xml = fg.rss_str(pretty=True)

    # feedgen doesn't natively support Podcasting 2.0; patch the XML to add
    # the xmlns:podcast namespace and <podcast:chapters> elements.
    raw_xml = _inject_podcast_chapters(raw_xml, sorted_episodes, config)

    output_path.write_bytes(raw_xml)


def _inject_podcast_chapters(raw_xml: bytes, episodes: list, config: dict) -> bytes:
    """
    1. Add xmlns:podcast namespace to the <rss> element.
    2. Insert <podcast:chapters> inside each <item> that has chapters.
    """
    xml_str = raw_xml.decode("utf-8")

    if 'xmlns:podcast=' not in xml_str:
        xml_str = xml_str.replace(
            "<rss ",
            f'<rss xmlns:podcast="{PODCAST_NS}" ',
            1,
        )

    chapters_lookup = {
        ep["video_id"]: ep.get("chapters_url", "")
        for ep in episodes
        if ep.get("chapters") and ep.get("chapters_url")
    }

    if not chapters_lookup:
        return xml_str.encode("utf-8")

    lines = xml_str.split("\n")
    result = []
    current_guid = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<guid"):
            start = stripped.find(">") + 1
            end = stripped.rfind("<")
            if start > 0 and end > start:
                current_guid = stripped[start:end]
        if stripped == "</item>" and current_guid in chapters_lookup:
            indent = line[: len(line) - len(line.lstrip())]
            chapters_tag = (
                f'{indent}  <podcast:chapters url="{chapters_lookup[current_guid]}" '
                f'type="application/json+chapters"/>'
            )
            result.append(chapters_tag)
            current_guid = None
        result.append(line)

    return "\n".join(result).encode("utf-8")
