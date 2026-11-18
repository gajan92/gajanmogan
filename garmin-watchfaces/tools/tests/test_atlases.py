import json
from pathlib import Path

import pytest
from PIL import Image

from make_fonts import ATLAS_SPECS, build_atlases

WIDTHS = Path(__file__).resolve().parents[2] / "mockups" / "reference" / "text-widths.json"


@pytest.fixture(scope="module")
def atlases(tmp_path_factory):
    out = tmp_path_factory.mktemp("atlas")
    return out, build_atlases(out)  # {atlas_id: {char: (x, y, w, h, advance, bearingX, bearingTop)}}


def test_every_charset_char_has_an_entry(atlases):
    _, a = atlases
    for spec in ATLAS_SPECS:
        assert set(a[spec.id]) == set(spec.chars), spec.id


def test_advances_are_proportional(atlases):
    _, a = atlases
    assert a["ARC85"]["M"][4] > a["ARC85"]["I"][4]


def test_arc85_has_heart_and_sun(atlases):
    _, a = atlases
    for ch in "♥☀":
        x, y, w, h, *_ = a["ARC85"][ch]
        assert w > 3 and h > 3


def test_atlas_png_is_white_with_alpha(atlases):
    out, _ = atlases
    im = Image.open(out / "atlas_arc85.png").convert("RGBA")
    covered = [p for p in im.get_flattened_data() if p[3] > 0]
    assert covered and all(p[:3] == (255, 255, 255) for p in covered)


def test_atlases_mc_lists_every_atlas(atlases):
    out, _ = atlases
    src = (out / "Atlases.mc").read_text()
    for spec in ATLAS_SPECS:
        assert f":{spec.id}" in src and f"atlas_{spec.id.lower()}" in src


@pytest.mark.skipif(not WIDTHS.exists(), reason="text-widths.json is written by Task 4")
def test_label_width_matches_mockup(atlases):
    _, a = atlases
    want = json.loads(WIDTHS.read_text())["82% · 6 DAYS"]
    got = sum(a["ARC85"][c][4] for c in "82% · 6 DAYS") + 1.2 * len("82% · 6 DAYS")
    assert abs(got - want) <= 1.5
