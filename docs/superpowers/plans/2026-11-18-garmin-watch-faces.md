# Garmin Watch Faces (Day Ring, Halo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two side-loadable/beta-installable Connect IQ watch faces for the Vivoactive 5 that match `garmin-watchfaces/mockups/final-faces.html` pixel-for-pixel within 1 px, plus a how-to deck.

**Architecture:** The HTML mockup is the layout reference: it is made data-driven, renders six fixed states, and exports (a) each face's static art as an opaque 390×390 PNG, (b) icon sprites, and (c) reference renders and element boxes. Python tools generate bitmap fonts, rotated-glyph atlases for curved text, settings XML, and compare simulator screenshots against the reference. Two Monkey C apps (`dayring/`, `halo/`) share `common/` code (pure logic, data snapshot, drawing helpers). Each draws its base PNG and then the live parts on top.

**Tech Stack:** Monkey C / Connect IQ SDK (on the owner's Mac), Python 3 + Pillow + numpy + pytest, Node + Playwright (Chromium) for the mockup renders.

**Spec:** `docs/superpowers/specs/2026-11-18-garmin-watch-faces-design.md`

**Where tasks run:** Tasks 1–5 run in the cloud session (no Garmin SDK needed). Tasks 6–11 need the owner's Mac with the SDK: either a Remote Control folder attached to this session, or a Claude session running on the Mac. Monkey C code in Tasks 7–8 can be written in the cloud, but it is only "done" once it is compiled and tested on the Mac.

## Global Constraints

- Device id `vivoactive5` (390×390 round AMOLED). Confirm the id and API level in Task 6.
- Pure black background `#000000`. Stat colours: HR `#FF4D4D`, steps `#3DD6F5`, fasting `#FF9F1C`, battery `#4CD964`, weather `#FFD60A`, calories `#FF5FA2`, sun events `#FFC247`. The eating state uses cream `#F2E3C6` (owner-approved).
- Time: Orbitron 900, hour `#FFFFFF`, colon+minutes `#FF9F1C`. Font size **65 px on Day Ring, 59 px on Halo**. The mockup computes 65.1 and 58.72. 24h shows a zero-padded hour; 12h has no leading zero. No seconds, no AM/PM.
- Weight is always in lb: `grams / 453.592`, one decimal, e.g. `172.8 LB`. Distance and temperature follow the watch settings.
- Missing data is never shown as `0`. The placeholders are `--` (number), `--:--` (time), `--°` (temperature) and `-- LB` (weight).
- Settings: `eatStart` default `720`, `eatEnd` default `1200` (minutes since midnight), in 30-minute choices. A hidden `refState` (default `0`) is used only by reference builds.
- Fixed labels are English and uppercase. Day and month names come from `Gregorian.info(..., FORMAT_MEDIUM)`, uppercased.
- No touch handling and no seconds updates. The face redraws once a minute; the HR trend refreshes at most every 5 minutes.
- **Alignment tolerance:** every element named in the reference boxes is within **±1 px** of the mockup. Items marked centred are within **0.75 px** of x = 195. No two named elements are closer than 2 px. This applies on every build and in every state.
- **Format rules** (identical in JS for the mockup and Monkey C for the watch):
  | Function | Examples |
  |---|---|
  | duration(min) | 111→`1H 51M`, 51→`51M`, 120→`2H`, 0→`0M` |
  | thousands(n) | 640→`640`, 2180→`2,180`, 99999→`99,999` |
  | kilo(n) (Halo steps, Day Ring goal) | 640→`640`, 6412→`6.4K`, 9999→`9.9K`, 10000→`10K`, 12345→`12.3K`, 99999→`99.9K` (always rounds down; a trailing `.0` is dropped) |
  | windowLabel(start, end) (Day Ring `EAT …`; always 24h) | 720,1200→`12–20`; 750,1200→`12:30–20:00` (both on the hour → hours only) |
  | hhmm(m, is24) | 991,true→`16:31`; 991,false→`4:31`; 461,true→`07:41` |

## Reference states (single source: `garmin-watchfaces/mockups/states.json`, written in Task 4)

| id | name | Differences from `reference` |
|---|---|---|
| 0 | reference | 10:09 Wed 18 Nov, 24h, eat 720–1200, HR 64, HR history = the 24 values in `final-faces.html`, steps 6412/10000, kcal total 2180 / active 640, 480000 cm, metric, 78400 g (172.8 lb), battery 82 / 6 days, 12 °C (H 14, L 6), clear sky, rise 461 (07:41), set 991 (16:31) |
| 1 | eating | 15:00, so the labels read `FAST IN 5H` and Halo shows `EATING · 3H / 8H` |
| 2 | missing | HR, HR history, weather, rise/set, weight, height and birth year are null; battery days null; active kcal null, so calories show the total only |
| 3 | h12single | 13:05 in 12h mode, so the time is `1:05` and sunset is `4:31` |
| 4 | large | steps 99999/10000, kcal 9999 / active 8888, 4219000 cm in statute (`26.2 MI`), weight 181400 g (`399.9 LB`), battery 100 / 30 days, HR 188, 40 °C (104 °F; H 43 °C = 109 °F, L 37 °C = 99 °F), statute units |
| 5 | midnight | 00:01 Thu 19 Nov, so the labels read `EAT IN 11H 59M`, the next event is `07:42 SUNRISE` (rise 462), and the fast is 4H 01M into 16H |

## Review Focus

1. **The eating window crosses midnight, or start equals end.** 18:00–02:00 must work. Equal start and end returns no fasting state, so the faces show the empty ring and `--` labels. Tested in Task 7.
2. **The phone is disconnected, or there is no weather, HR or profile.** Every slot shows its placeholder and nothing reads 0. Covered by state 2 in Tasks 4, 8, 9 and 10.
3. **Text width varies.** A 1-digit 12h hour, `99,999`, `399.9 LB`, `104°` and `100%` must stay centred and must not overlap. Covered by states 3 and 4 in the mockup audit and the screenshot compare.
4. **Day rollover.** Date change, next sunrise vs sunset, and a fast spanning midnight. Covered by `Sun.next` tests in Task 7 and state 5.
5. **Settings changed in Garmin Connect apply without restarting the face.** `onSettingsChanged` must trigger a redraw. Checked by hand on the watch in Task 11.

---

### Task 1: Tool scaffold, fonts, and straight-text bitmap fonts (cloud)

**Files:**
- Create: `garmin-watchfaces/tools/requirements.txt` (`Pillow>=10.1`, `numpy`, `pytest`)
- Create: `garmin-watchfaces/tools/fetch_fonts.py`, `garmin-watchfaces/tools/fonts/` (TTFs + `OFL.txt`)
- Create: `garmin-watchfaces/tools/make_fonts.py`
- Create: `garmin-watchfaces/tools/tests/conftest.py` (adds `tools/` to `sys.path`), `garmin-watchfaces/tools/tests/test_make_fonts.py`
- Generates: `garmin-watchfaces/common/resources/fonts/*.fnt|*.png`, `garmin-watchfaces/common/resources/fonts/fonts.xml`, `garmin-watchfaces/common/source/FontMetrics.mc`

**Interfaces:**
- Produces: font resource ids (below) as `Rez.Fonts.<ID>`. `FontMetrics.ink(fontId as Symbol, ch as Char) as [Number, Number]` gives (inkTop, inkBottom) in px relative to the baseline, with top negative. `FontMetrics.base(fontId) as Number` is the BMFont `base`.

- [ ] **Step 1: Fetch fonts.** `fetch_fonts.py` requests `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Orbitron:wght@900` with an old desktop User-Agent so the CSS lists `.ttf` URLs from fonts.gstatic.com. It saves `Inter-<weight>.ttf` and `Orbitron-900.ttf`. Commit them along with `OFL.txt` (SIL OFL 1.1 text, plus the copyright lines for Inter and Orbitron).

- [ ] **Step 2: Write failing tests** in `test_make_fonts.py`:

```python
from make_fonts import FONT_SPECS, build_all, parse_fnt

def test_every_spec_char_is_in_fnt(tmp_path):
    build_all(tmp_path)
    for spec in FONT_SPECS:
        fnt = parse_fnt(tmp_path / f"{spec.id.lower()}.fnt")
        assert {chr(c) for c in fnt.char_ids} == set(spec.chars)

def test_time_digit_ink_heights_match_mockup(tmp_path):
    m = build_all(tmp_path)          # returns {font_id: {char: (top, bottom)}}
    top, bottom = m["TIME_DR"]["0"]; assert abs((bottom - top) - 47) <= 1   # mockup: 143..190
    top, bottom = m["TIME_HA"]["0"]; assert abs((bottom - top) - 43) <= 1   # mockup: 145.8..188.8

def test_aod_outline_is_hollow(tmp_path):
    build_all(tmp_path)
    from PIL import Image
    lit = lambda p: sum(1 for a in Image.open(p).getchannel("A").getdata() if a > 64)
    assert lit(tmp_path / "time_dr_aod_0.png") < 0.4 * lit(tmp_path / "time_dr_0.png")

def test_metrics_mc_lists_every_font(tmp_path):
    build_all(tmp_path)
    src = (tmp_path / "FontMetrics.mc").read_text()
    for spec in FONT_SPECS: assert f":{spec.id}" in src
```

- [ ] **Step 3: Run tests and confirm they fail.** Run `pytest garmin-watchfaces/tools/tests/test_make_fonts.py -v`. They should fail with `ModuleNotFoundError: make_fonts`.

- [ ] **Step 4: Implement `make_fonts.py`.** It needs `FONT_SPECS: list[FontSpec(id, ttf, size, chars, outline_px=0)]`, `build_all(out_dir) -> dict` and `parse_fnt(path)`. Each font is written as an AngelCode BMFont text `.fnt` with a single white-on-alpha `.png` page, rasterised with Pillow at the exact (possibly fractional) size. Outline variants stroke the glyph at 2 px and leave the inside empty. With no argument, `build_all` writes into the repo paths above, and also writes `fonts.xml` and `FontMetrics.mc`. The spec table, where `A-Z` means the uppercase alphabet:

  | id | font | size | chars |
  |---|---|---|---|
  | TIME_DR, TIME_DR_AOD (outline) | Orbitron-900 | 65 | `0123456789:` |
  | TIME_HA, TIME_HA_AOD (outline) | Orbitron-900 | 59 | `0123456789:` |
  | DR_DATE | Inter-700 | 12 | `A-Z0-9 ` |
  | DR_SUNTIME | Inter-600 | 11.5 | `0123456789:-` |
  | DR_SUNLABEL | Inter-600 | 8 | `SUNRIET` |
  | DR_PILL | Inter-700 | 10.5 | `EATFSINHM0123456789 -` |
  | DR_KMLB | Inter-600 | 10.5 | `0123456789.KMILB -` |
  | DR_SUBVAL | Inter-700 | 14 | `0123456789,-°` |
  | DR_SUBSMALL | Inter-500 | 7 | `/0123456789,-` |
  | DR_KCAL | Inter-700 | 6.5 | `KCAL` |
  | DR_WXLOHI | Inter-600 | 7 | `0123456789-°` |
  | HA_B11 | Inter-700 | 11 | `EATFSINHMK%0123456789 .,-` |
  | HA_B15 | Inter-700 | 15 | `0123456789-°` |
  | HA_DAY | Inter-500 | 15 | `A-Z` |
  | HA_SUBLABEL | Inter-600 | 6 | `STEPDAY 0123456789-` |
  | HA_SUBTOTAL | Inter-500 | 6 | `/0123456789-` |
  | HA_WXHL | Inter-600 | 7.5 | `HL0123456789 -°` |

- [ ] **Step 5: Run the tests and confirm they pass.** Then run `python garmin-watchfaces/tools/make_fonts.py` to generate the repo files.

- [ ] **Step 6: Commit** the tools, fonts and generated resources: `feat(watchfaces): bitmap font pipeline`.

### Task 2: Curved-text glyph atlases (cloud)

**Files:**
- Modify: `garmin-watchfaces/tools/make_fonts.py` (add atlases)
- Test: `garmin-watchfaces/tools/tests/test_atlases.py`
- Generates: `garmin-watchfaces/common/resources/drawables/atlas_{arc75,arc85,arc9}.png`, `garmin-watchfaces/common/source/Atlases.mc`

**Interfaces:**
- Consumes: `FontSpec` and Pillow rendering from Task 1. Task 4's sprites `heart_7.png` and `sun_8.png` supply the special glyphs, so build Task 4's sprite export first if needed. Otherwise draw a placeholder and re-run after Task 4.
- Produces: `Atlases.glyph(atlasId as Symbol, ch as Char) as [x, y, w, h, advance, bearingX, bearingTop]` (px, with `bearingTop` measured from the baseline, negative going up). Also `Atlases.bitmap(atlasId) as Symbol` (the `Rez.Drawables` id). The atlas ids are `:ARC75` (Inter-600 7.5), `:ARC85` (Inter-600 8.5) and `:ARC9` (Inter-800 9). The charset for ARC75 and ARC85 is `A-Z0-9 %–:·/.,`. ARC85 also gets `♥☀` from the sprites, and ARC9 is `0123456789`.

- [ ] **Step 1: Write failing tests:** every charset char has an entry; `advance('M') > advance('I')`; ARC85 contains `♥` and `☀`; the atlas PNG pixels are white (RGB 255) with coverage carried only in alpha; and the advances summed for `82% · 6 DAYS`, plus 1.2 px of letter-spacing per glyph, are within ±1.5 px of the width the mockup's `getComputedTextLength` gives. Task 4 writes those widths to `mockups/reference/text-widths.json`. Until then, skip that one test with `pytest.mark.skipif`.
- [ ] **Step 2: Run the tests and confirm they fail.** Run `pytest garmin-watchfaces/tools/tests/test_atlases.py -v`.
- [ ] **Step 3: Implement `build_atlases(out_dir)`.** Pack the glyphs into one PNG per atlas with 1 px padding, and write `Atlases.mc` as constant dictionaries.
- [ ] **Step 4: Run the tests and confirm they pass.** Then regenerate the repo files.
- [ ] **Step 5: Commit:** `feat(watchfaces): curved-text glyph atlases`.

### Task 3: Settings resources (cloud)

**Files:**
- Create: `garmin-watchfaces/tools/make_settings.py`, `garmin-watchfaces/tools/tests/test_make_settings.py`
- Generates: `garmin-watchfaces/common/resources/settings/properties.xml`, `settings.xml`, and `garmin-watchfaces/common/resources/strings/settings_strings.xml`

**Interfaces:**
- Produces: the properties `eatStart` (number, 720), `eatEnd` (number, 1200) and `refState` (number, 0, with no setting entry). Read them with `Application.Properties.getValue("eatStart")`.

- [ ] **Step 1: Write failing tests:** each list setting has 48 `listEntry` values `0, 30, …, 1410`, labelled `00:00` … `23:30` in order; the titles are `Eating window starts` and `Eating window ends`; the defaults are 720 and 1200; `refState` is in `properties.xml` but not in `settings.xml`; and every string id referenced in `settings.xml` exists in the strings file.
- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `make_settings.py`.** It generates the three XML files.
- [ ] **Step 4: Run the tests and confirm they pass.** Then generate the repo files.
- [ ] **Step 5: Commit:** `feat(watchfaces): eating-window settings`.

### Task 4: Data-driven mockups, base layers, sprites, reference renders (cloud)

**Files:**
- Modify: `garmin-watchfaces/mockups/final-faces.html`
- Create: `garmin-watchfaces/mockups/states.json`, `garmin-watchfaces/tools/export_layers.js`, `garmin-watchfaces/tools/tests/test_export_layers.py`
- Generates: `garmin-watchfaces/dayring/resources/drawables/dayring_base.png`, `garmin-watchfaces/halo/resources/drawables/halo_base.png`, `garmin-watchfaces/common/resources/drawables/{heart_12,heart_7,sunset_14,sunrise_14,sun_8,halo_head,wx_*_14,wx_*_10}.png`, `garmin-watchfaces/mockups/reference/<face>-<state>.png|.json`, `garmin-watchfaces/mockups/reference/text-widths.json`

**Interfaces:**
- Produces:
  - `states.json`: the six states from the table above as raw inputs (minutes, grams, °C, flags), not formatted strings.
  - `<face>-<state>.json`: `{ "issues": [...], "boxes": { id: {left, right, top, bottom, text, center} } }`.
  - The page accepts `?face=dayring|halo&state=<name>&layer=full|base`.

- [ ] **Step 1: Write failing tests** in `test_export_layers.py`, which runs `node tools/export_layers.js` once in a session-scoped fixture:

```python
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
        assert im.size == (390, 390) and im.mode == "RGB"
        assert im.getpixel((195, 167)) == (0, 0, 0)  # the time sits here; base must leave it empty
```

- [ ] **Step 2: Run the tests and confirm they fail.**

- [ ] **Step 3: Refactor `final-faces.html`.** `dayRing(d)` and `halo(d)` take a state object. Their strings come from JS versions of the Format rules, plus `fastingState` and `nextSun`, which mirror Task 7. Every drawing call is wrapped in `S(...)` (static) or `D(...)` (dynamic), and `layer=base` renders only the `S` parts.
  - **Static:** Day Ring gauge tracks, tick scales, HR zone arc, weather gradient arc, subdial discs/ticks/tracks, and the pill background. Halo guilloché, bezel ticks and numerals, chapter ring, the 16 halo ticks, the halo track, subdial discs/ticks/tracks, and the divider.
  - **Dynamic:** everything else, including the Day Ring 24h band, its separators and numerals (they sit on the daily-changing band), and the fasting track (it depends on settings).
  - **Eating state:** Day Ring fills the dotted segment in cream up to "now" and shows an empty orange track. Halo shows a cream gradient ring over the eating length, with `EATING · <elapsed> / <total>`.
  - **Missing state:** markers whose value is null are hidden.
  - Add `text` and `center` to every audited box. The existing audit (centring, 2 px gap, dial insets, ring clearance) stays as is.

- [ ] **Step 4: Implement `export_layers.js`.** It uses Playwright at deviceScaleFactor 1 with a 390×390 viewport per face. It writes the base PNGs, the reference PNG and JSON for all 2 × 6 combinations, and `text-widths.json` for each curved label. It also writes the sprite PNGs, rendered from the mockup's icon functions with a transparent background:

  | Sprite | Size |
  |---|---|
  | heart | 12 px and 7 px |
  | sunset, sunrise | 14 px |
  | sun | 8 px |
  | Halo head | 22 px, glow included |
  | weather icons | 14 px and 10 px: `clear, clear_night, partly, cloudy, rain, snow, thunder, fog, wind` |

- [ ] **Step 5: Run the tests and confirm they pass.** Run `pytest garmin-watchfaces/tools/tests/test_export_layers.py -v`. If a state has audit issues, fix the mockup layout, not the test. Show any layout change to the owner as an image before committing.

- [ ] **Step 6: Look at all 12 reference renders at 2×** and check the curved labels (the audit can't see them), especially state 4's `99,999 / 10K STEPS`. Re-run Task 2's skipped width test.

- [ ] **Step 7: Commit:** `feat(watchfaces): data-driven mockups and exported layers`.

### Task 5: Screenshot compare tool (cloud)

**Files:**
- Create: `garmin-watchfaces/tools/compare.py`, `garmin-watchfaces/tools/tests/test_compare.py`

**Interfaces:**
- Consumes: the `mockups/reference/<face>-<state>.png|.json` files and `<face>_base.png` from Task 4.
- Produces: `compare(face: str, state: str, shot: Path, out_dir: Path, crop: tuple|None = None) -> Report`. A `Report` has `located: (x, y, scale)`, `offsets: {id: (dx, dy)}`, `missing: [id]` and `passed: bool`. It writes `side_by_side.png` and `diff.png`. CLI: `python compare.py --face dayring --state reference --shot sim.png [--crop x,y,w,h]`, exiting 0 on pass and 1 on fail.

- [ ] **Step 1: Write failing tests:**

```python
def test_locates_face_at_1x_and_2x(tmp_path, ref_png):
    for scale, pos in ((1, (123, 77)), (2, (40, 210))):
        shot = paste_on_grey(ref_png, scale, pos, canvas=(900, 1100))
        r = compare("dayring", "reference", shot, tmp_path)
        assert r.located == (pos[0], pos[1], scale) and r.passed

def test_flags_element_moved_2px(tmp_path):
    shot = shift_region(ref("halo", "reference"), box("halo", "reference", "time"), dx=2)
    r = compare("halo", "reference", shot, tmp_path)
    assert not r.passed and r.offsets["time"] == (2, 0)

def test_flags_missing_element(tmp_path):
    shot = blank_region(ref("dayring", "reference"), box("dayring", "reference", "pill"))
    assert "pill" in compare("dayring", "reference", shot, tmp_path).missing
```

- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `compare.py`.** Locate the face by normalised cross-correlation of the base layer against the screenshot (numpy FFT), trying scale 1 and then 2. Subtract the base layer from both the cropped screenshot and the reference, so only dynamic ink remains. For each box, take a window padded by 6 px and threshold the luminance difference at > 40. Measure the ink bounding box in both images, and record the offset of the bbox centres, rounded to whole pixels. The result passes only if every |dx| and |dy| ≤ 1 and nothing is missing.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit:** `feat(watchfaces): screenshot alignment compare`.

### Task 6: Mac setup and capability spike (Mac) — GATE

**Files:**
- Create: `garmin-watchfaces/spike/` (a minimal watch-face app), `garmin-watchfaces/SPIKE.md`

- [ ] **Step 1: Owner setup.** I'll give the owner these steps:
  1. Install VS Code and the **Monkey C** extension.
  2. Install the Connect IQ **SDK Manager**, sign in, and download the latest SDK and the Vivoactive 5 device.
  3. Run `mkdir -p ~/garmin-dev && cd ~/garmin-dev && openssl genrsa -out developer_key.pem 4096 && openssl pkcs8 -topk8 -inform PEM -outform DER -in developer_key.pem -out developer_key.der -nocrypt`.
  4. Clone the repo, check out `claude/focused-mccarthy-ic0fh4`, and share that folder via Remote Control. If cloud folder access isn't available, start a Claude session on the Mac in that folder.
- [ ] **Step 2: Write the spike app.** Its `onUpdate` draws, in order:
  1. a 390×390 PNG;
  2. an alpha-blended sprite over a coloured arc;
  3. text in a custom BMFont (`TIME_DR`);
  4. one atlas glyph drawn with `dc.drawBitmap2(x, y, atlas, {:bitmapX…, :bitmapWidth…, :tintColor => 0xFF4D4D, :transform => rotated 30°})`;
  5. an arc in `Graphics.createColor(0x80, 0xFF, 0x9F, 0x1C)`.
- [ ] **Step 3: Build and run.** Run `monkeyc -f garmin-watchfaces/spike/monkey.jungle -d vivoactive5 -o build/spike.prg -y ~/garmin-dev/developer_key.der`, start the simulator with `connectiq`, then run `monkeydo build/spike.prg vivoactive5`.
- [ ] **Step 4: Record in `SPIKE.md`:**
  1. the device id and API level, from the SDK's `Devices/vivoactive5/compiler.json`;
  2. whether each of the 5 draw tests works (yes/no, with a screenshot);
  3. the unit-test command that works (expected: `monkeyc … --unit-test` then `monkeydo build/x.prg vivoactive5 -t`);
  4. how to set `refState` in the simulator (expected: File → Edit Persistent Storage → Application.Properties);
  5. how to get a screenshot of the screen at a known scale;
  6. whether the simulator's AMOLED burn-in check runs in low-power mode.
- [ ] **Step 5: GATE.** If any of the 5 draw tests fails, stop and report to the owner with options. A failed rotated glyph (test 4) means curved text needs another method; the spec says to bring layout alternatives. Otherwise, commit: `chore(watchfaces): capability spike findings`.

### Task 7: Shared pure logic with unit tests (write in the cloud, verify on the Mac)

**Files:**
- Create: `garmin-watchfaces/common/source/{Geometry,Format,Units,Fasting,Calories,Sun}.mc`
- Test: `garmin-watchfaces/common/test/{Geometry,Format,Units,Fasting,Calories,Sun}Test.mc`

**Interfaces:**
- Produces:
  - `Geometry.toGarminDeg(f as Float) as Float`: `f` is the fraction clockwise from 12 o'clock; returns Garmin degrees (0 = 3 o'clock, counter-clockwise positive) in [0, 360).
  - `Geometry.point(cx as Float, cy as Float, r as Float, f as Float) as [Float, Float]`
  - `Geometry.dayFraction(minuteOfDay as Number) as Float`: noon at top.
  - `Geometry.hrFraction(bpm as Number) as Float`: clamped over 40–190.
  - `Format.duration(min as Number) as String`, `Format.thousands(n as Number) as String`, `Format.kilo(n as Number) as String`, `Format.hhmm(minuteOfDay as Number, is24 as Boolean) as String`, `Format.windowLabel(start as Number, end as Number) as String`
  - `Format.clock(hour as Number, minute as Number, is24 as Boolean) as [String, String]`
  - `Units.lb(grams as Number or Null) as String`, `Units.distance(cm as Number, statute as Boolean) as [String, String]`, `Units.temp(celsius as Number or Null, fahrenheit as Boolean) as String`
  - `Fasting.compute(now as Number, eatStart as Number, eatEnd as Number) as Fasting.State or Null`. `State` has `isEating as Boolean`, `elapsed as Number`, `total as Number`, `minutesLeft as Number` and `progress as Float`.
  - `Calories.active(totalKcal as Number, weightG as Number or Null, heightCm as Number or Null, birthYear as Number or Null, isMale as Boolean, year as Number, minuteOfDay as Number) as Number or Null`
  - `Sun.next(now as Number, rise as Number or Null, set as Number or Null) as [Boolean, Number] or Null`: returns `[isSunset, minuteOfDay]`.

- [ ] **Step 1: Write failing tests.** Use one `(:test)` function per row, built from `Test.assertEqual`:

  | Call | Expected |
  |---|---|
  | `toGarminDeg(0.0)`, `(0.25)`, `(0.5)`, `(0.75)` | 90, 0, 270, 180 |
  | `dayFraction(720)`, `(1080)`, `(0)`, `(360)` | 0.0, 0.25, 0.5, 0.75 |
  | `hrFraction(40)`, `(64)`, `(190)`, `(30)`, `(200)` | 0.0, 0.16, 1.0, 0.0, 1.0 |
  | the Format examples | the Format rules table in Global Constraints |
  | `clock(10,9,true)`, `(7,5,true)`, `(13,5,false)`, `(0,30,false)`, `(12,0,false)` | `["10","09"]`, `["07","05"]`, `["1","05"]`, `["12","30"]`, `["12","00"]` |
  | `lb(78400)`, `lb(181400)`, `lb(null)` | `"172.8"`, `"399.9"`, `"--"` |
  | `distance(480000,false)`, `distance(4219000,true)` | `["4.8","KM"]`, `["26.2","MI"]` |
  | `temp(12,false)`, `temp(12,true)`, `temp(40,true)`, `temp(null,false)` | `"12"`, `"54"`, `"104"`, `"--"` |
  | `Fasting.compute(609,720,1200)` | not eating, elapsed 849, total 960, left 111 |
  | `Fasting.compute(900,720,1200)` | eating, elapsed 180, total 480, left 300 |
  | `Fasting.compute(720,720,1200)` / `(1200,720,1200)` | eating with elapsed 0, left 480 / fasting with elapsed 0, left 960 |
  | `Fasting.compute(60,1080,120)` / `(600,1080,120)` | eating, elapsed 420, total 480, left 60 / fasting, elapsed 480, total 960, left 480 |
  | `Fasting.compute(600,720,720)` | `null` |
  | `Calories.active(1368,78400,178,1990,true,2026,609)` | 640 (BMR 1721.5 × 609/1440 = 728) |
  | `Calories.active(900,60000,165,1990,false,2026,720)` | 255 |
  | `Calories.active(500,78400,178,1990,true,2026,609)` | 0 |
  | `Calories.active(1368,null,178,1990,true,2026,609)` | `null` |
  | `Sun.next(609,461,991)`, `(1000,461,991)`, `(1,462,991)`, `(609,null,null)` | `[true,991]`, `[false,461]`, `[false,462]`, `null` |

- [ ] **Step 2: Run the tests on the Mac and confirm they fail.** Use the unit-test command from SPIKE.md against a test jungle that includes `common/source` and `common/test`.
- [ ] **Step 3: Implement the modules.**
  - BMR uses Mifflin–St Jeor: `10·kg + 6.25·cm − 5·age + (male ? 5 : −161)`, with `age = year − birthYear`.
  - Active calories are `round(total − BMR × minuteOfDay/1440)`, clamped at 0.
  - All fasting arithmetic is done modulo 1440.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit:** `feat(watchfaces): shared logic with unit tests`.

### Task 8: Data snapshot (live + fixtures) and drawing helpers

**Files:**
- Create: `garmin-watchfaces/common/source/Snapshot.mc`, `garmin-watchfaces/common/source/Draw.mc`, `garmin-watchfaces/common/source/Icons.mc`, `garmin-watchfaces/tools/make_fixtures.py`
- Generates: `garmin-watchfaces/common/source/Fixtures.mc` (annotated `(:refdata)`)
- Test: `garmin-watchfaces/common/test/SnapshotTest.mc`, `garmin-watchfaces/common/test/DrawTest.mc`, `garmin-watchfaces/tools/tests/test_make_fixtures.py`

**Interfaces:**
- Consumes: `states.json` (Task 4), and `FontMetrics` and `Atlases` (Tasks 1–2).
- Produces:
  - `Snapshot.Data` has these fields: `hour, minute, minuteOfDay, is24, dayName, dayNum, monthName, hr, hrHistory, steps, stepGoal, kcalTotal, kcalActive, distanceCm, statute, weightG, battery, batteryDays, tempC, hiC, loC, fahrenheit, condition, riseMin, setMin, eatStart, eatEnd`. Anything unavailable is `null`.
  - `Snapshot.load() as Snapshot.Data`. The `(:live)` version reads the sources in spec §6.4. The `(:refdata)` version returns `Fixtures.state(Properties.getValue("refState"))`.
  - `Icons.weather(condition as Number or Null, isNight as Boolean, size as 10|14) as Symbol or Null`. `isNight` means the time is after sunset or before sunrise. Map `Weather.CONDITION_*` groups as follows; unknown or `null` → `null`:
    | Icon | Conditions |
    |---|---|
    | `clear` (`clear_night` at night) | clear, fair |
    | `partly` | partly cloudy, mostly clear, thin clouds |
    | `cloudy` | cloudy, mostly cloudy |
    | `rain` | any rain, showers, drizzle, freezing rain |
    | `snow` | snow, sleet, ice, hail, flurries, wintry mix |
    | `thunder` | any thunderstorm |
    | `fog` | fog, haze, mist, smoke, dust, sand, ash |
    | `wind` | windy, squall, tropical storm, hurricane, tornado |
  - `Draw.gradientArc(dc, cx, cy, r, width, f0, f1, colors as Array<Number>, roundCaps as Boolean)`: segments every 1/260 of a turn, matching the mockup's `gradArcC`.
  - `Draw.ticks(dc, cx, cy, r0, r1, f0, f1, count, color, width, majorEvery, majorColor, majorWidth)`
  - `Draw.textWidth(font as Symbol, text as String, spacing as Float) as Float`
  - `Draw.text(dc, x, cy, font, text, spacing, color, justify)`: draws with the ink centred vertically on `cy`. The baseline is `cy + (inkBottom + inkTop)/2·(−1)`, where inkTop and inkBottom are the min/max over the string's glyphs, the same as the mockup's `vt()`.
  - `Draw.radialText(dc, atlasId, text, r, fCenter, spacing, color, anchor as :start|:middle|:end, offsetPx as Float)` and the pure helper `Draw.radialPlacements(advances as Array<Float>, spacing, r, fCenter, anchor, offsetPx) as Array<[Float, Float, Float]>`, which gives the (x, y, rotation) of each glyph's baseline-centre.

- [ ] **Step 1: Write failing tests.**
  - `test_make_fixtures.py`: every state in `states.json` appears in `Fixtures.mc` with the same field values.
  - `SnapshotTest.mc`: `Fixtures.state(0).hour == 10`, `.weightG == 78400`, `Fixtures.state(2).hr == null`.
  - `IconsTest.mc`: `weather(CONDITION_CLEAR, true, 14) == :wx_clear_night_14`, `weather(CONDITION_THUNDERSTORMS, false, 10) == :wx_thunder_10`, `weather(null, false, 14) == null`.
  - Add to `FormatTest.mc`: `windowLabel(720,1200) == "12–20"`, `windowLabel(750,1200) == "12:30–20:00"`, `kilo(10000) == "10K"`.
  - `DrawTest.mc` for `radialPlacements`. In the top half (`fCenter` 0.0, `:middle`) the placements are mirror-symmetric in x around 195. Glyph rotations equal `f·2π`. In the bottom half (`fCenter` 0.5) rotations equal `f·2π + π` and the glyphs run left to right. The sum of the arc steps equals Σadvance + n·spacing (SVG letter-spacing includes the last glyph). `:end` with `offsetPx` −8 ends 8 px before the centre plus the trailing spacing, matching the mockup's `ctAt`.
- [ ] **Step 2: Run the tests and confirm they fail** (pytest and Mac unit tests).
- [ ] **Step 3: Implement `make_fixtures.py`, `Snapshot.mc` and `Draw.mc`.** In the top half, the glyph baseline sits on radius `r` with "up" pointing outward. In the bottom half, the path runs counter-clockwise and "up" points inward, the same as the mockup's `ct()`/`ctAt()`. Each glyph is drawn with `drawBitmap2`, using the atlas sub-rect, `:tintColor` and a rotate-about-glyph-centre `AffineTransform`.
- [ ] **Step 4: Run the tests and confirm they pass.**
- [ ] **Step 5: Commit:** `feat(watchfaces): data snapshot and drawing helpers`.

### Task 9: Day Ring face (Mac)

**Files:**
- Create: `garmin-watchfaces/dayring/manifest.xml`, `monkey.jungle`, `reference.jungle`, `source/DayRingApp.mc`, `source/DayRingView.mc`, `resources/drawables/drawables.xml`, `resources/strings/strings.xml` (app name `Day Ring`)
- Create: `garmin-watchfaces/verification/dayring/` (screenshots and compare outputs, committed)

**Interfaces:**
- Consumes: everything in `common/`. `dayring_base.png` comes from Task 4.

- [ ] **Step 1: Set up the manifest and jungles.**
  - `manifest.xml`: type `watchface`, product `vivoactive5`, the minimum API from SPIKE.md, a newly generated UUID, and the permissions `SensorHistory` and `UserProfile`.
  - `monkey.jungle`: `sourcePath = source;../common/source`, `resourcePath = resources;../common/resources`, `base.excludeAnnotations = refdata`.
  - `reference.jungle`: the same, but with `base.excludeAnnotations = live`.
- [ ] **Step 2: Implement `DayRingView.onUpdate(dc)`.** Draw order, with geometry exactly as in `final-faces.html` `dayRing(d)`:
  1. base bitmap at (0, 0);
  2. 24h band (night/day gradients from `riseMin`/`setMin`, or 06:00/18:00 when null), then hour separators and `ARC9` numerals;
  3. sun pins (hidden when null);
  4. fasting track, then eating dots or cream fill, then the progress gradient with a glow underlay (two wider arcs, +6 px at alpha 0x40 and +3 px at alpha 0x70);
  5. the needle, with a glow underlay;
  6. gauge fills and markers;
  7. curved labels;
  8. centre column;
  9. subdial contents.

  Rows use measured widths, the same way the mockup's `row()` and `cgroup` do. Also implement `onEnterSleep`/`onExitSleep`: the always-on screen draws `TIME_DR_AOD` with the hour in `#9A9A9A` and the minutes in `#B8701A`. Its position cycles through offsets `(0,0),(2,0),(0,2),(−2,0),(0,−2)` by `minute % 5`.
  `DayRingApp.onSettingsChanged()` calls `WatchUi.requestUpdate()`.
- [ ] **Step 3: Build and run the reference build.** Run `monkeyc -f garmin-watchfaces/dayring/reference.jungle -d vivoactive5 -o build/dayring-ref.prg -y ~/garmin-dev/developer_key.der`, then `monkeydo build/dayring-ref.prg vivoactive5`.
- [ ] **Step 4: Compare all six states.** For `refState` 0–5, take a screenshot (method from SPIKE.md) and run `python garmin-watchfaces/tools/compare.py --face dayring --state <name> --shot <png>`. Expected: `PASS` for all six. Fix the code, not the tolerance.
- [ ] **Step 5: Visual review at 2×.** Read each `side_by_side.png` at 2× zoom and review every region: the curved labels, the arcs and glow (which the compare can't measure), and the subdial insets.
- [ ] **Step 6: Check always-on mode.** In the simulator's low-power mode, the burn-in check should report no violations. Save a screenshot.
- [ ] **Step 7: Commit** the code and `verification/dayring/*`: `feat(watchfaces): Day Ring face`.

### Task 10: Halo face (Mac)

**Files:**
- Create: the same layout under `garmin-watchfaces/halo/` (`HaloApp.mc`, `HaloView.mc`, app name `Halo`, a new UUID), plus `garmin-watchfaces/verification/halo/`

**Interfaces:**
- Consumes: everything in `common/`. `halo_base.png` comes from Task 4.

- [ ] **Step 1: Set up the manifest and jungles,** the same as Task 9 Step 1.
- [ ] **Step 2: Implement `HaloView.onUpdate(dc)`.** Draw order, as in `halo(d)`:
  1. base bitmap;
  2. halo progress (orange gradient, or cream when eating) with a glow underlay;
  3. the white start marker;
  4. the head sprite `halo_head.png` centred on the progress point;
  5. curved labels with `ARC85` (the separator `·` is exactly at fraction 0.5);
  6. centre column;
  7. the HR + weather pair, centred as a whole with the divider between them. The HR trend is a 24-point polyline in a 34×16 px box, hidden when null, and the history is cached in a member variable for 5 minutes.
  8. subdial fills and values.

  The always-on screen uses `TIME_HA_AOD`, the same as Task 9.
- [ ] **Step 3: Compare all six states,** following Task 9 Steps 3–6 with `--face halo`. Expected: `PASS` for all six, a clean burn-in check, and the 2× visual review done.
- [ ] **Step 4: Commit:** `feat(watchfaces): Halo face`.

### Task 11: Install on the watch, private beta, README (Mac and owner)

**Files:**
- Create: `garmin-watchfaces/README.md` (setup, build, test, compare and install commands from Tasks 6–10)

- [ ] **Step 1: Build the release apps.** Run `monkeyc -f garmin-watchfaces/<face>/monkey.jungle -d vivoactive5 -o build/<Face>.prg -y ~/garmin-dev/developer_key.der -r` for each face.
- [ ] **Step 2: Side-load to the watch.** The owner connects the watch over USB, opens **OpenMTP** (macOS needs an MTP app), and copies both `.prg` files to `GARMIN/APPS`. On the watch, both faces appear in Watch Face → Add New.
- [ ] **Step 3: Check on the wrist.** The time matches the phone. The step count matches Garmin's own widget. Battery and weather are present when the phone is connected. Weight reads in lb. Raising the wrist after the screen dims shows the full face, and the dimmed face shows only the time.
- [ ] **Step 4: Export the beta packages.** Run `monkeyc -f garmin-watchfaces/<face>/monkey.jungle -e -o build/<Face>.iq -y ~/garmin-dev/developer_key.der -r`. The owner uploads both `.iq` files as **Beta** apps at the Connect IQ developer dashboard, then installs them from the Connect IQ Store app.
- [ ] **Step 5: Check settings.** The owner changes the eating window in Garmin Connect to 13:00–21:00. The face shows the new window within a minute, without being reselected (Review Focus 5).
- [ ] **Step 6: Commit** the README: `docs(watchfaces): build and install guide`.

### Task 12: How-to deck (cloud)

**Files:**
- An Artifact deck made from the Slides type (not a repo file). Use the reference renders from `garmin-watchfaces/mockups/reference/` and the verified screenshots.

- [ ] **Step 1:** Run `Artifact` quickstart with `intent: "slides"`, and create the deck from the Slides type it returns.
- [ ] **Step 2: Content, about one idea per slide:**
  1. what the two faces are;
  2. installing them (beta store, or USB side-load);
  3. switching faces;
  4. setting the eating window in Garmin Connect;
  5. a **Day Ring tour**: an annotated render with a callout for every element (24h band, pins, fasting track and needle, the three gauges, the centre column, both subdials);
  6. a **Halo tour**, with the same treatment;
  7. how the fasting and eating states look (states 0 and 1);
  8. what `--` means and when it appears (state 2);
  9. data notes: active calories are an estimate and can differ from Garmin Connect by a few percent; weight comes from the Garmin profile; weather needs the phone;
  10. what the dimmed always-on screen shows;
  11. troubleshooting.
- [ ] **Step 3: Check every slide's callouts for alignment** at 2×, then share the link with the owner.
