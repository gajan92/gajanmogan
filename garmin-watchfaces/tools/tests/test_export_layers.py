import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]          # garmin-watchfaces/
REF = ROOT / "mockups" / "reference"
STATE_NAMES = ["reference", "eating", "missing", "h12single", "large", "midnight"]


class Exported:
    def audit(self, face, state):
        return json.loads((REF / f"{face}-{state}.json").read_text())

    def base(self, face):
        return Image.open(ROOT / face / "resources" / "drawables" / f"{face}_base.png")


@pytest.fixture(scope="session")
def exported():
    subprocess.run(["node", str(ROOT / "tools" / "export_layers.js")], check=True, cwd=ROOT,
                   timeout=600)
    return Exported()


def test_every_state_has_no_alignment_issues(exported):
    for face in ("dayring", "halo"):
        for state in STATE_NAMES:
            assert exported.audit(face, state)["issues"] == [], (face, state)


def test_state_texts(exported):
    t = lambda f, s, i: exported.audit(f, s)["boxes"][i]["text"]
    assert t("dayring", "reference", "time") == "10:09"
    assert t("dayring", "eating", "pill") == "FAST IN 5H"
    assert t("dayring", "missing", "kg") == "-- LB"
    assert t("halo", "h12single", "time") == "1:05"
    assert t("halo", "large", "s2v") == "99.9K"
    assert t("dayring", "midnight", "pill") == "EAT IN 11H 59M"
    assert t("dayring", "midnight", "sunset").endswith("SUNRISE")


def test_base_layers_are_opaque_390_and_static_only(exported):
    for face in ("dayring", "halo"):
        im = exported.base(face)
        assert im.size == (390, 390)
        assert im.convert("RGBA").getchannel("A").getextrema() == (255, 255)
        assert im.convert("RGB").getpixel((195, 167)) == (0, 0, 0)  # the time sits here


def test_states_json_matches_state_names(exported):
    states = json.loads((ROOT / "mockups" / "states.json").read_text())
    assert [s["name"] for s in states] == STATE_NAMES
    assert states[0]["weightG"] == 78400 and states[2]["hr"] is None


def test_sprites_exist_with_transparency(exported):
    d = ROOT / "common" / "resources" / "drawables"
    names = ["heart_12", "sunset_14", "sunrise_14", "halo_head_fast", "halo_head_eat"]
    names += [f"wx_{w}_{s}" for w in ("clear", "clear_night", "partly", "cloudy", "rain", "snow",
                                      "thunder", "fog", "wind") for s in (10, 14)]
    for n in names:
        im = Image.open(d / f"{n}.png").convert("RGBA")
        lo, hi = im.getchannel("A").getextrema()
        assert lo == 0 and hi > 200, n
    xml = (d / "sprites.xml").read_text()
    assert all(f'id="{n}"' in xml for n in names)
