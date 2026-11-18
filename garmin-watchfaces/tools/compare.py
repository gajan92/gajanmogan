"""Compare a simulator screenshot of a watch face against the mockup reference render.

1. Locate the 390×390 face inside the screenshot (any position, scale 1 or 2) by normalised
   cross-correlation of the face's static base layer.
2. Remove the base layer from both the cropped screenshot and the reference, leaving only the
   live ink (text, gauge fills, markers).
3. For every audited element box from the mockup, compare the ink bounding boxes: the centre
   offset must be within ±1 px, and an element present in the reference must be present.

CLI:  python compare.py --face dayring --state reference --shot sim.png [--crop x,y,w,h] [--out dir]
Exit code 0 = pass, 1 = fail.
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "mockups" / "reference"
SIZE = 390
PAD = 6          # px around each element box
INK = 40         # luminance difference that counts as ink
TOL = 1          # px


@dataclass
class Report:
    located: tuple
    offsets: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    passed: bool = False


def lum(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float64)


def ncc_locate(img: np.ndarray, tpl: np.ndarray):
    """Best (x, y, score) of tpl inside img by normalised cross-correlation (FFT)."""
    H, W = img.shape
    h, w = tpl.shape
    if h > H or w > W:
        return None
    t = tpl - tpl.mean()
    tn = np.sqrt((t ** 2).sum())
    shape = (H + h - 1, W + w - 1)
    corr = np.fft.irfft2(np.fft.rfft2(img, shape) * np.fft.rfft2(t[::-1, ::-1], shape), shape)
    corr = corr[h - 1:H, w - 1:W]

    def box_sum(a):
        c = np.pad(a.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return c[h:, w:] - c[:-h, w:] - c[h:, :-w] + c[:-h, :-w]

    s1, s2 = box_sum(img), box_sum(img ** 2)
    var = np.maximum(s2 - s1 ** 2 / (h * w), 1e-9)
    score = corr / (np.sqrt(var) * tn)
    y, x = np.unravel_index(np.argmax(score), score.shape)
    return int(x), int(y), float(score[y, x])


def locate(shot: Image.Image, base: Image.Image):
    best = None
    for scale in (1, 2):
        tpl = base if scale == 1 else base.resize((SIZE * scale,) * 2, Image.LANCZOS)
        hit = ncc_locate(lum(shot), lum(tpl))
        if hit and (best is None or hit[2] > best[3]):
            best = (hit[0], hit[1], scale, hit[2])
    return best[:3]


def ink_bbox(diff: np.ndarray, win):
    x0, y0, x1, y1 = win
    ys, xs = np.nonzero(diff[y0:y1, x0:x1] > INK)
    if len(xs) == 0:
        return None
    return xs.min() + x0, ys.min() + y0, xs.max() + x0, ys.max() + y0


def compare(face: str, state: str, shot, out_dir, crop=None) -> Report:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reference = Image.open(REF / f"{face}-{state}.png").convert("RGB")
    boxes = json.loads((REF / f"{face}-{state}.json").read_text())["boxes"]
    base = Image.open(ROOT / face / "resources" / "drawables" / f"{face}_base.png").convert("RGB")
    shot_img = Image.open(shot).convert("RGB")

    if crop:
        x, y, w, _ = crop
        located = (x, y, w // SIZE)
    else:
        located = locate(shot_img, base)
    x, y, scale = located
    face_img = shot_img.crop((x, y, x + SIZE * scale, y + SIZE * scale))
    if scale != 1:
        face_img = face_img.resize((SIZE, SIZE), Image.BOX)

    d_shot = np.abs(lum(face_img) - lum(base))
    d_ref = np.abs(lum(reference) - lum(base))
    report = Report(located=located)
    for el, b in boxes.items():
        win = (max(0, int(b["left"]) - PAD), max(0, int(b["top"]) - PAD),
               min(SIZE, int(b["right"]) + PAD + 1), min(SIZE, int(b["bottom"]) + PAD + 1))
        r, s = ink_bbox(d_ref, win), ink_bbox(d_shot, win)
        if r is None:
            continue
        if s is None:
            report.missing.append(el)
            continue
        dx = round(((s[0] + s[2]) - (r[0] + r[2])) / 2)
        dy = round(((s[1] + s[3]) - (r[1] + r[3])) / 2)
        report.offsets[el] = (dx, dy)
    report.passed = not report.missing and all(abs(a) <= TOL and abs(b) <= TOL
                                                for a, b in report.offsets.values())

    heat = Image.fromarray(np.clip(np.abs(lum(face_img) - lum(reference)) * 3, 0, 255).astype(np.uint8))
    heat.convert("RGB").save(out_dir / "diff.png")
    side = Image.new("RGB", (SIZE * 3 + 20, SIZE), (40, 40, 40))
    for i, im in enumerate((reference, face_img, heat.convert("RGB"))):
        side.paste(im, (i * (SIZE + 10), 0))
    side.save(out_dir / "side_by_side.png")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--face", required=True, choices=["dayring", "halo"])
    ap.add_argument("--state", required=True)
    ap.add_argument("--shot", required=True)
    ap.add_argument("--crop", help="x,y,w,h of the face in the screenshot (skips auto-locate)")
    ap.add_argument("--out", default="compare-out")
    a = ap.parse_args(argv)
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    r = compare(a.face, a.state, a.shot, Path(a.out), crop)
    bad = {k: v for k, v in r.offsets.items() if abs(v[0]) > TOL or abs(v[1]) > TOL}
    print(f"located at {r.located}")
    for k, v in sorted(r.offsets.items()):
        print(f"  {'FAIL' if k in bad else 'ok  '} {k}: dx {v[0]:+d}, dy {v[1]:+d}")
    for k in r.missing:
        print(f"  MISSING {k}")
    print("PASS" if r.passed else "FAIL")
    return 0 if r.passed else 1


if __name__ == "__main__":
    sys.exit(main())
