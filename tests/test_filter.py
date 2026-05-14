import pytest
from pathlib import Path
from filter import is_visual_heavy, DEFAULT_KEYWORDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_allowlist(tmp_path: Path, channels: list[str]) -> Path:
    f = tmp_path / "allowlist.txt"
    f.write_text("\n".join(channels), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# 1. Default keyword matches — parametrized over all keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("keyword", DEFAULT_KEYWORDS)
def test_keyword_in_title(keyword):
    heavy, reason = is_visual_heavy(
        title=f"Watch this {keyword} now",
        description="nothing relevant here",
        channel="SomeChannel",
    )
    assert heavy is True
    assert keyword.lower() in reason.lower()
    assert "title" in reason


@pytest.mark.parametrize("keyword", DEFAULT_KEYWORDS)
def test_keyword_in_description_first_500(keyword):
    heavy, reason = is_visual_heavy(
        title="Podcast episode",
        description=f"In this video we do a {keyword} of the topic",
        channel="SomeChannel",
    )
    assert heavy is True
    assert "description" in reason


# ---------------------------------------------------------------------------
# 2. Case insensitivity
# ---------------------------------------------------------------------------

def test_case_insensitive_title_upper():
    heavy, _ = is_visual_heavy("TUTORIAL ON PYTHON", "", "Chan")
    assert heavy is True


def test_case_insensitive_title_mixed():
    heavy, _ = is_visual_heavy("TuToRiAl", "", "Chan")
    assert heavy is True


def test_case_insensitive_description():
    heavy, _ = is_visual_heavy("Podcast", "This is a WALKTHROUGH of the thing", "Chan")
    assert heavy is True


# ---------------------------------------------------------------------------
# 3. Title vs description matching + reason content
# ---------------------------------------------------------------------------

def test_match_in_title_reason_says_title():
    heavy, reason = is_visual_heavy("Tutorial intro", "No keywords here at all", "Chan")
    assert heavy is True
    assert "title" in reason


def test_match_in_description_reason_says_description():
    heavy, reason = is_visual_heavy("Deep Dive episode", "A walkthrough of the API today", "Chan")
    assert heavy is True
    assert "description" in reason


def test_no_match_returns_false_none():
    heavy, reason = is_visual_heavy(
        title="Podcast episode 42",
        description="Just talking about stuff with a guest today",
        channel="SomePodcast",
    )
    assert heavy is False
    assert reason is None


# ---------------------------------------------------------------------------
# 4. 500-char description boundary
# ---------------------------------------------------------------------------

def test_keyword_beyond_500_chars_not_matched():
    padding = "x" * 510
    heavy, _ = is_visual_heavy(
        title="Podcast",
        description=padding + " tutorial ",
        channel="Chan",
    )
    assert heavy is False


def test_keyword_within_500_chars_is_matched():
    prefix = "a" * 490
    heavy, _ = is_visual_heavy(
        title="Clean title",
        description=prefix + "demo: stuff",
        channel="Chan",
    )
    assert heavy is True


def test_keyword_starting_at_char_500_not_matched():
    # "tutorial" starts at exactly index 500 — outside the [:500] window
    prefix = "b" * 500
    heavy, _ = is_visual_heavy(
        title="Nothing",
        description=prefix + "tutorial",
        channel="Chan",
    )
    assert heavy is False


# ---------------------------------------------------------------------------
# 5. Channel allowlist
# ---------------------------------------------------------------------------

def test_allowlist_overrides_keyword_in_title(tmp_path):
    allowlist = make_allowlist(tmp_path, ["TrustedPodcast"])
    heavy, reason = is_visual_heavy(
        title="Tutorial: Python Security",
        description="walkthrough of the code",
        channel="TrustedPodcast",
        allowlist_path=allowlist,
    )
    assert heavy is False
    assert reason is None


def test_allowlist_case_insensitive(tmp_path):
    allowlist = make_allowlist(tmp_path, ["TrustedPodcast"])
    heavy, _ = is_visual_heavy(
        title="Tutorial",
        description="",
        channel="TRUSTEDPODCAST",
        allowlist_path=allowlist,
    )
    assert heavy is False


def test_allowlist_does_not_affect_unlisted_channel(tmp_path):
    allowlist = make_allowlist(tmp_path, ["TrustedPodcast"])
    heavy, _ = is_visual_heavy(
        title="Tutorial",
        description="",
        channel="RandomChannel",
        allowlist_path=allowlist,
    )
    assert heavy is True


def test_empty_allowlist_file(tmp_path):
    allowlist = make_allowlist(tmp_path, [])
    heavy, _ = is_visual_heavy(
        title="Screencast demo",
        description="",
        channel="AnyChannel",
        allowlist_path=allowlist,
    )
    assert heavy is True


def test_allowlist_ignores_comment_lines(tmp_path):
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("# TrustedPodcast\n", encoding="utf-8")
    heavy, _ = is_visual_heavy(
        title="Tutorial",
        description="",
        channel="TrustedPodcast",
        allowlist_path=allowlist,
    )
    assert heavy is True


def test_missing_allowlist_file(tmp_path):
    nonexistent = tmp_path / "does_not_exist.txt"
    heavy, _ = is_visual_heavy(
        title="Tutorial",
        description="",
        channel="TrustedPodcast",
        allowlist_path=nonexistent,
    )
    assert heavy is True


def test_allowlist_strips_whitespace(tmp_path):
    allowlist = make_allowlist(tmp_path, ["  SpaceyChannel  "])
    heavy, _ = is_visual_heavy(
        title="Tutorial",
        description="",
        channel="SpaceyChannel",
        allowlist_path=allowlist,
    )
    assert heavy is False


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------

def test_empty_title_and_description():
    heavy, reason = is_visual_heavy("", "", "SomeChannel")
    assert heavy is False
    assert reason is None


def test_title_match_takes_priority_over_description(tmp_path):
    """When both title and description match, title reason is reported (checked first)."""
    heavy, reason = is_visual_heavy(
        title="Build a REST API tutorial",
        description="walkthrough of the concepts",
        channel="Chan",
    )
    assert heavy is True
    assert "title" in reason


def test_custom_keywords_list():
    heavy, reason = is_visual_heavy(
        title="Some custom trigger word here",
        description="",
        channel="Chan",
        keywords=["custom trigger word"],
    )
    assert heavy is True


def test_custom_keywords_list_no_match():
    heavy, _ = is_visual_heavy(
        title="tutorial walkthrough",
        description="",
        channel="Chan",
        keywords=["custom trigger word"],
    )
    assert heavy is False
