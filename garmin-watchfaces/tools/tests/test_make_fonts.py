from PIL import Image, ImageChops, ImageFilter, ImageFont

from make_fonts import FONT_DIR, FONT_SPECS, build_all, glyph_mask, parse_fnt


def test_every_spec_char_is_in_fnt(tmp_path):
    build_all(tmp_path)
    for spec in FONT_SPECS:
        fnt = parse_fnt(tmp_path / f"{spec.id.lower()}.fnt")
        assert {chr(c) for c in fnt.char_ids} == set(spec.chars), spec.id


def test_time_digit_ink_heights_match_mockup(tmp_path):
    m = build_all(tmp_path)  # {font_id: {char: (top, bottom)}}
    top, bottom = m["TIME_DR"]["0"]
    assert abs((bottom - top) - 47) <= 1  # mockup ink: y 143..190
    top, bottom = m["TIME_HA"]["0"]
    assert abs((bottom - top) - 43) <= 1  # mockup ink: y 145.8..188.8


def test_aod_outline_is_hollow():
    # The deep interior of each filled stroke (3 px in from every edge) must be unlit in the outline.
    font = ImageFont.truetype(str(FONT_DIR / "Orbitron-900.ttf"), 65)
    for ch in "0123456789":
        fill, fl, ft = glyph_mask(font, ch, 0)
        ring, rl, rt = glyph_mask(font, ch, 2)
        canvas = Image.new("L", (ring.width + 20, ring.height + 20), 0)
        canvas.paste(fill, (fl - rl + 10, ft - rt + 10))
        interior = canvas.filter(ImageFilter.MinFilter(7))
        outline = Image.new("L", canvas.size, 0)
        outline.paste(ring, (10, 10))
        assert interior.getbbox() is not None, ch
        overlap = ImageChops.multiply(interior.point(lambda a: 255 if a > 128 else 0),
                                      outline.point(lambda a: 255 if a > 64 else 0))
        assert overlap.getbbox() is None, ch


def test_png_is_white_with_alpha_coverage(tmp_path):
    build_all(tmp_path)
    im = Image.open(tmp_path / "dr_date_0.png").convert("RGBA")
    covered = [p for p in im.get_flattened_data() if p[3] > 0]
    assert covered and all(p[:3] == (255, 255, 255) for p in covered)


def test_metrics_mc_lists_every_font(tmp_path):
    build_all(tmp_path)
    src = (tmp_path / "FontMetrics.mc").read_text()
    for spec in FONT_SPECS:
        assert f":{spec.id}" in src
