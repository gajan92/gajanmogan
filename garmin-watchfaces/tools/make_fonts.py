"""Generate Connect IQ bitmap fonts (AngelCode BMFont text format) from the TTFs in fonts/.

Each font is a .fnt plus one white-on-alpha .png page. Glyphs are rasterised with Pillow at the
exact (possibly fractional) pixel size the mockup uses. Also writes fonts.xml (Connect IQ
resource list) and FontMetrics.mc (per-glyph ink extents, used to centre text exactly like
the mockup's vt()).
"""
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent          # garmin-watchfaces/
FONT_DIR = Path(__file__).resolve().parent / "fonts"
RES_DIR = ROOT / "common" / "resources" / "fonts"
SRC_DIR = ROOT / "common" / "source"

AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"


@dataclass(frozen=True)
class FontSpec:
    id: str
    ttf: str
    size: float
    chars: str
    outline_px: int = 0


FONT_SPECS = [
    FontSpec("TIME_DR", "Orbitron-900.ttf", 65, DIGITS + ":"),
    FontSpec("TIME_DR_AOD", "Orbitron-900.ttf", 65, DIGITS + ":", outline_px=2),
    FontSpec("TIME_HA", "Orbitron-900.ttf", 59, DIGITS + ":"),
    FontSpec("TIME_HA_AOD", "Orbitron-900.ttf", 59, DIGITS + ":", outline_px=2),
    FontSpec("DR_DATE", "Inter-700.ttf", 12, AZ + DIGITS + " "),
    FontSpec("DR_SUNTIME", "Inter-600.ttf", 11.5, DIGITS + ":-"),
    FontSpec("DR_SUNLABEL", "Inter-600.ttf", 8, "SUNRIET"),
    FontSpec("DR_PILL", "Inter-700.ttf", 10.5, "EATFSINHM" + DIGITS + " -"),
    FontSpec("DR_KMLB", "Inter-600.ttf", 10.5, DIGITS + ".KMILB -"),
    FontSpec("DR_SUBVAL", "Inter-700.ttf", 14, DIGITS + ",-°"),
    FontSpec("DR_SUBSMALL", "Inter-500.ttf", 7, "/" + DIGITS + ",-"),
    FontSpec("DR_KCAL", "Inter-700.ttf", 6.5, "KCAL"),
    FontSpec("DR_WXLOHI", "Inter-600.ttf", 7, DIGITS + "-°"),
    FontSpec("HA_B11", "Inter-700.ttf", 11, "EATFSINHMK%" + DIGITS + " .,-"),
    FontSpec("HA_B9", "Inter-700.ttf", 9, "K%" + DIGITS + " .,-"),
    FontSpec("HA_B15", "Inter-700.ttf", 15, DIGITS + "-°"),
    FontSpec("HA_DAY", "Inter-500.ttf", 15, AZ),
    FontSpec("HA_SUBLABEL", "Inter-600.ttf", 6, "STEPDAY " + DIGITS + "-"),
    FontSpec("HA_SUBTOTAL", "Inter-500.ttf", 6, "/" + DIGITS + "-"),
    FontSpec("HA_WXHL", "Inter-600.ttf", 7.5, "HL" + DIGITS + " -°"),
]


ARC_CHARS = AZ + DIGITS + " %–:·/.,"
ATLAS_SPECS = [
    FontSpec("ARC75", "Inter-600.ttf", 7.5, ARC_CHARS),
    FontSpec("ARC85", "Inter-600.ttf", 8.5, ARC_CHARS + "♥☀"),
    FontSpec("ARC9", "Inter-800.ttf", 9, DIGITS),
]
DRAWABLE_DIR = ROOT / "common" / "resources" / "drawables"
SS = 8  # supersampling for the vector-drawn special glyphs


@dataclass
class Fnt:
    char_ids: list
    base: int
    line_height: int


def unique(chars: str) -> str:
    return "".join(dict.fromkeys(chars))


def glyph_mask(font: ImageFont.FreeTypeFont, ch: str, outline_px: int):
    """Return (mask L-image, left, top) of the glyph's ink, positioned relative to the
    baseline origin; None for blank glyphs (space)."""
    l, t, r, b = font.getbbox(ch, anchor="ls")
    if r <= l or b <= t:
        return None
    pad = outline_px + 2
    w, h = r - l + 2 * pad, b - t + 2 * pad
    fill = Image.new("L", (w, h), 0)
    ImageDraw.Draw(fill).text((pad - l, pad - t), ch, font=font, fill=255, anchor="ls")
    if outline_px:
        stroked = Image.new("L", (w, h), 0)
        ImageDraw.Draw(stroked).text((pad - l, pad - t), ch, font=font, fill=255, anchor="ls",
                                     stroke_width=outline_px // 2, stroke_fill=255)
        inner = fill.filter(ImageFilter.MinFilter(2 * (outline_px - outline_px // 2) + 1))
        fill = ImageChops.subtract(stroked, inner)
    box = fill.getbbox()
    if box is None:
        return None
    mask = fill.crop(box)
    return mask, box[0] - pad + l, box[1] - pad + t


def build_font(spec: FontSpec, out_dir: Path) -> dict:
    font = ImageFont.truetype(str(FONT_DIR / spec.ttf), spec.size)
    ascent, descent = font.getmetrics()
    stem = spec.id.lower()
    glyphs = []                                  # (ch, mask|None, left, top, advance)
    for ch in unique(spec.chars):
        g = glyph_mask(font, ch, spec.outline_px)
        adv = round(font.getlength(ch))
        glyphs.append((ch, *(g if g else (None, 0, 0)), adv))

    # simple shelf packing
    page_w = 512 if spec.size < 30 else 1024
    x = y = shelf = 0
    places = []
    for ch, mask, left, top, adv in glyphs:
        w, h = (mask.size if mask else (0, 0))
        if x + w + 1 > page_w:
            x, y, shelf = 0, y + shelf + 1, 0
        places.append((x, y))
        x += w + 1
        shelf = max(shelf, h)
    page_h = y + shelf + 1
    page = Image.new("RGBA", (page_w, page_h), (255, 255, 255, 0))
    for (ch, mask, left, top, adv), (px, py) in zip(glyphs, places):
        if mask:
            white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
            white.putalpha(mask)
            page.paste(white, (px, py))
    page.save(out_dir / f"{stem}_0.png")

    lines = [
        f'info face="{spec.ttf[:-4]}" size={round(spec.size)} bold=0 italic=0 charset="" unicode=1 '
        f'stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1',
        f"common lineHeight={ascent + descent} base={ascent} scaleW={page_w} scaleH={page_h} "
        f"pages=1 packed=0",
        f'page id=0 file="{stem}_0.png"',
        f"chars count={len(glyphs)}",
    ]
    ink = {}
    for (ch, mask, left, top, adv), (px, py) in zip(glyphs, places):
        w, h = (mask.size if mask else (0, 0))
        lines.append(f"char id={ord(ch)} x={px} y={py} width={w} height={h} "
                     f"xoffset={left} yoffset={ascent + top if mask else 0} xadvance={adv} "
                     f"page=0 chnl=15")
        ink[ch] = (top, top + h) if mask else (0, 0)
    (out_dir / f"{stem}.fnt").write_text("\n".join(lines) + "\n")
    return {"ink": ink, "base": ascent}


def parse_fnt(path: Path) -> Fnt:
    ids, base, lh = [], 0, 0
    for line in Path(path).read_text().splitlines():
        kv = dict(p.split("=", 1) for p in line.split()[1:] if "=" in p)
        if line.startswith("common "):
            base, lh = int(kv["base"]), int(kv["lineHeight"])
        elif line.startswith("char "):
            ids.append(int(kv["id"]))
    return Fnt(ids, base, lh)


def mc_char(ch: str) -> str:
    return "'\\''" if ch == "'" else f"'{ch}'"


def write_metrics_mc(results: dict, path: Path) -> None:
    out = ["// Generated by tools/make_fonts.py — do not edit.",
           "import Toybox.Lang;", "", "module FontMetrics {", "", "    const BASE = {"]
    out += [f"        :{fid} => {r['base']}," for fid, r in results.items()]
    out += ["    };", "", "    // char => [inkTop, inkBottom] relative to the baseline (top negative)",
            "    const INK = {"]
    for fid, r in results.items():
        entries = ", ".join(f"{mc_char(c)} => [{t}, {b}]" for c, (t, b) in r["ink"].items())
        out.append(f"        :{fid} => {{ {entries} }},")
    out += ["    };", "",
            "    function ink(fontId as Symbol, ch as Char) as Array<Number> {",
            "        var e = (INK[fontId] as Dictionary)[ch];",
            "        return e == null ? [0, 0] : e as Array<Number>;",
            "    }", "",
            "    function base(fontId as Symbol) as Number {",
            "        return BASE[fontId] as Number;",
            "    }", "}", ""]
    path.write_text("\n".join(out))


def write_fonts_xml(path: Path) -> None:
    rows = [f'    <font id="{s.id}" filename="{s.id.lower()}.fnt" antialias="true"/>'
            for s in FONT_SPECS]
    path.write_text("<fonts>\n" + "\n".join(rows) + "\n</fonts>\n")


def special_glyph(ch: str, size: float):
    """♥ and ☀ are not in Inter; draw them in the mockup's icon style.
    Returns (mask, left, top, advance) relative to the baseline origin."""
    if ch == "♥":
        w = round(size * 0.82)                       # ~7 px at 8.5
        big = Image.new("L", (w * SS, w * SS), 0)
        d = ImageDraw.Draw(big)
        r = w * SS / 4
        d.ellipse((0, 0, 2 * r, 2 * r), fill=255)
        d.ellipse((2 * r, 0, 4 * r, 2 * r), fill=255)
        d.polygon([(0.15 * r, 1.45 * r), (3.85 * r, 1.45 * r), (2 * r, 3.7 * r)], fill=255)
        mask = big.resize((w, w), Image.LANCZOS)
    else:                                            # ☀: ring + 8 rays, like the sun icon
        w = round(size * 0.95)
        big = Image.new("L", (w * SS, w * SS), 0)
        d = ImageDraw.Draw(big)
        c, lw = w * SS / 2, max(1, round(0.11 * w * SS))
        rr = 0.22 * w * SS
        d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=255, width=lw)
        import math
        for i in range(8):
            a = i * math.pi / 4
            d.line((c + 0.36 * w * SS * math.cos(a), c + 0.36 * w * SS * math.sin(a),
                    c + 0.49 * w * SS * math.cos(a), c + 0.49 * w * SS * math.sin(a)), fill=255, width=lw)
        mask = big.resize((w, w), Image.LANCZOS)
    cap = round(size * 0.727)                        # Inter cap height ≈ 0.727 em
    top = -round((cap + w) / 2)                      # vertically centred on the cap height
    return mask, 0, top, w + round(size * 0.25)


def build_atlas(spec: FontSpec, out_dir: Path) -> dict:
    font = ImageFont.truetype(str(FONT_DIR / spec.ttf), spec.size)
    entries, tiles = {}, []
    for ch in unique(spec.chars):
        if ch in "♥☀":
            mask, left, top, adv = special_glyph(ch, spec.size)
        else:
            g = glyph_mask(font, ch, 0)
            adv = font.getlength(ch)
            mask, left, top = g if g else (None, 0, 0)
        tiles.append((ch, mask, left, top, adv))
    x, page_w, h = 0, sum((t[1].width + 1) if t[1] else 0 for t in tiles) + 1, \
        max((t[1].height for t in tiles if t[1]), default=1) + 2
    page = Image.new("RGBA", (page_w, h), (255, 255, 255, 0))
    for ch, mask, left, top, adv in tiles:
        if mask:
            white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
            white.putalpha(mask)
            page.paste(white, (x, 1))
            entries[ch] = (x, 1, mask.width, mask.height, round(adv, 2), left, top)
            x += mask.width + 1
        else:
            entries[ch] = (0, 0, 0, 0, round(adv, 2), 0, 0)
    page.save(out_dir / f"atlas_{spec.id.lower()}.png")
    return entries


def write_atlases_mc(atlases: dict, path: Path) -> None:
    out = ["// Generated by tools/make_fonts.py — do not edit.",
           "import Toybox.Lang;", "import Toybox.WatchUi;", "", "module Atlases {", "",
           "    // char => [x, y, w, h, advance, bearingX, bearingTop] (bearingTop: from baseline, up is negative)",
           "    const GLYPHS = {"]
    for aid, e in atlases.items():
        items = ", ".join(f"{mc_char(c)} => [{x}, {y}, {w}, {h}, {float(adv):.2f}, {bx}, {bt}]"
                          for c, (x, y, w, h, adv, bx, bt) in e.items())
        out.append(f"        :{aid} => {{ {items} }},")
    out += ["    };", "",
            "    function glyph(atlasId as Symbol, ch as Char) as Array or Null {",
            "        return (GLYPHS[atlasId] as Dictionary)[ch] as Array or Null;",
            "    }", "",
            "    function bitmap(atlasId as Symbol) as ResourceId {"]
    for aid in atlases:
        out.append(f"        if (atlasId == :{aid}) {{ return Rez.Drawables.atlas_{aid.lower()}; }}")
    out += ["        return Rez.Drawables.atlas_arc85;", "    }", "}", ""]
    path.write_text("\n".join(out))


def build_atlases(out_dir: Path | None = None) -> dict:
    img_dir = Path(out_dir) if out_dir else DRAWABLE_DIR
    src_dir = Path(out_dir) if out_dir else SRC_DIR
    img_dir.mkdir(parents=True, exist_ok=True)
    atlases = {s.id: build_atlas(s, img_dir) for s in ATLAS_SPECS}
    rows = [f'    <bitmap id="atlas_{a.lower()}" filename="atlas_{a.lower()}.png"/>' for a in atlases]
    (img_dir / "atlases.xml").write_text("<drawables>\n" + "\n".join(rows) + "\n</drawables>\n")
    write_atlases_mc(atlases, src_dir / "Atlases.mc")
    return atlases


def build_all(out_dir: Path | None = None) -> dict:
    res_dir = Path(out_dir) if out_dir else RES_DIR
    src_dir = Path(out_dir) if out_dir else SRC_DIR
    res_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    results = {s.id: build_font(s, res_dir) for s in FONT_SPECS}
    write_fonts_xml(res_dir / "fonts.xml")
    write_metrics_mc(results, src_dir / "FontMetrics.mc")
    return {fid: r["ink"] for fid, r in results.items()}


if __name__ == "__main__":
    build_all()
    build_atlases()
    print(f"wrote {len(FONT_SPECS)} fonts and {len(ATLAS_SPECS)} atlases")
