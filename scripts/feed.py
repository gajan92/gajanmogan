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
        fe.description(_sanitize_description(ep.get("description", "")))

        pub = datetime.fromisoformat(ep["ripped_at"].replace("Z", "+00:00"))
        fe.pubDate(pub)

        fe.enclosure(
            url=ep["download_url"],
            length=str(ep["file_size_bytes"]),
            type="audio/mpeg",
        )

        fe.podcast.itunes_duration(_parse_duration(ep["duration_seconds"]))
        fe.podcast.itunes_explicit("no")

        if ep.get("thumbnail_url"):
            fe.podcast.itunes_image(ep["thumbnail_url"])

        # Podcasting 2.0 chapters
        chapters = ep.get("chapters") or []
        if chapters:
            _write_chapters_file(chapters, ep["video_id"], feed_dir)
            chapters_url = ep.get("chapters_url", "")
            if chapters_url:
                fe.load_extension("dc")  # ensure DC extension doesn't conflict
                # Add <podcast:chapters> as a custom element via feedgen's
                # _FeedEntry.__dict__ injection isn't supported cleanly, so we
                # store it and post-process the XML after rss_str().
        # chapters_url is handled via post-processing below

    raw_xml = fg.rss_str(pretty=True)

    # Inject podcast namespace declaration and <podcast:chapters> elements.
    # feedgen doesn't natively support Podcasting 2.0, so we patch the XML.
    raw_xml = _inject_podcast_chapters(raw_xml, sorted_episodes, config)

    output_path.write_bytes(raw_xml)


def _inject_podcast_chapters(raw_xml: bytes, episodes: list, config: dict) -> bytes:
    """
    1. Add xmlns:podcast namespace to the <rss> element.
    2. Insert <podcast:chapters> inside each <item> that has chapters.
    """
    xml_str = raw_xml.decode("utf-8")

    # Add namespace to <rss ...>
    if 'xmlns:podcast=' not in xml_str:
        xml_str = xml_str.replace(
            "<rss ",
            f'<rss xmlns:podcast="{PODCAST_NS}" ',
            1,
        )

    # Build a lookup: video_id -> chapters_url
    chapters_lookup = {
        ep["video_id"]: ep.get("chapters_url", "")
        for ep in episodes
        if ep.get("chapters") and ep.get("chapters_url")
    }

    if not chapters_lookup:
        return xml_str.encode("utf-8")

    # Insert <podcast:chapters> before </item> for matching episodes
    lines = xml_str.split("\n")
    result = []
    current_guid = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<guid"):
            # Extract guid value
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
