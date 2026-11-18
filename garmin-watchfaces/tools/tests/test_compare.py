import json
from pathlib import Path

from PIL import Image

from compare import compare

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "mockups" / "reference"


def ref(face, state):
    return Image.open(REF / f"{face}-{state}.png").convert("RGB")


def base(face):
    return Image.open(ROOT / face / "resources" / "drawables" / f"{face}_base.png").convert("RGB")


def box(face, state, el):
    b = json.loads((REF / f"{face}-{state}.json").read_text())["boxes"][el]
    return [round(b["left"]) - 4, round(b["top"]) - 4, round(b["right"]) + 4, round(b["bottom"]) + 4]


def paste_on_grey(face_img, scale, pos, canvas, out):
    img = face_img.resize((390 * scale, 390 * scale), Image.LANCZOS) if scale != 1 else face_img
    c = Image.new("RGB", canvas, (60, 60, 64))
    c.paste(img, pos)
    c.save(out)
    return out


def shift_region(face, state, el, dx, out):
    img, b = ref(face, state), box(face, state, el)
    region = img.crop(b)
    img.paste(base(face).crop(b), b[:2])          # clear the element...
    img.paste(region, (b[0] + dx, b[1]))           # ...and put it back dx px to the right
    img.save(out)
    return out


def blank_region(face, state, el, out):
    img, b = ref(face, state), box(face, state, el)
    img.paste(base(face).crop(b), b[:2])
    img.save(out)
    return out


def test_locates_face_at_1x_and_2x(tmp_path):
    for scale, pos in ((1, (123, 77)), (2, (40, 210))):
        shot = paste_on_grey(ref("dayring", "reference"), scale, pos, (900, 1100), tmp_path / f"s{scale}.png")
        r = compare("dayring", "reference", shot, tmp_path)
        assert r.located == (pos[0], pos[1], scale)
        assert r.passed, r.offsets


def test_flags_element_moved_2px(tmp_path):
    shot = shift_region("halo", "reference", "time", 2, tmp_path / "moved.png")
    r = compare("halo", "reference", shot, tmp_path)
    assert not r.passed and r.offsets["time"] == (2, 0)


def test_flags_missing_element(tmp_path):
    shot = blank_region("dayring", "reference", "pill", tmp_path / "blank.png")
    r = compare("dayring", "reference", shot, tmp_path)
    assert "pill" in r.missing and not r.passed


def test_writes_review_images(tmp_path):
    shot = paste_on_grey(ref("halo", "eating"), 1, (10, 10), (500, 500), tmp_path / "e.png")
    compare("halo", "eating", shot, tmp_path / "out")
    assert (tmp_path / "out" / "side_by_side.png").exists() and (tmp_path / "out" / "diff.png").exists()
