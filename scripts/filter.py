from pathlib import Path

DEFAULT_KEYWORDS = [
    "tutorial",
    "walkthrough",
    "how to build",
    "let's build",
    "let's code",
    "code along",
    "from scratch",
    "demo:",
    "screencast",
    "step by step",
    "implementing",
    "build a",
    "ide setup",
    "debugger",
]

ALLOWLIST_PATH = Path(__file__).parent.parent / "data" / "allowlist.txt"


def _load_allowlist(path: Path = ALLOWLIST_PATH) -> set[str]:
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        line.strip().lower()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    }


def is_visual_heavy(
    title: str,
    description: str,
    channel: str,
    keywords: list[str] = DEFAULT_KEYWORDS,
    allowlist_path: Path = ALLOWLIST_PATH,
) -> tuple[bool, str | None]:
    """
    Returns (True, reason) if the episode should be skipped (visual-heavy content).
    Returns (False, None) if it should be ripped.

    Channel allowlist overrides all keyword matches.
    Only the first 500 chars of description are scanned.
    """
    allowlist = _load_allowlist(allowlist_path)
    if channel.strip().lower() in allowlist:
        return (False, None)

    title_lower = title.lower()
    desc_lower = description[:500].lower()

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in title_lower:
            return (True, f"matched: {kw!r} in title")
        if kw_lower in desc_lower:
            return (True, f"matched: {kw!r} in description (first 500 chars)")

    return (False, None)
