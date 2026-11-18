# Prompt for the Mac session (paste everything below the line)

---

You are taking over a project that was planned and partly built in a cloud Claude Code session.
You are now running locally on my Mac, which has (or will have) Garmin's Connect IQ SDK, the
simulator and my watch connected over USB. Continue the work from **Task 6**. Read this whole
message before doing anything.

## How I like to work

- **Always use the AskUserQuestion tool when you need a decision from me** — give clear options,
  mark your recommendation, and let me pick. Don't ask questions in plain chat.
- When there's something visual to judge, **send me an image (PNG)** — my Mac app has trouble
  previewing HTML files.
- **Alignment must be perfect, and you must double-check it every single time** you render or
  build anything: nothing off-centre, overlapping, cramped against a ring or clipped by the round
  edge. Use the automated checks *and* look at the result yourself at 2× zoom. Never loosen a
  tolerance to make a check pass — fix the drawing.
- I approved the designs and decisions below; don't re-open them. If something truly can't be
  built as designed, stop and bring me options (with images) via AskUserQuestion.
- Keep me posted in short lines; report failures honestly with the output.
- Run at extra-high effort for the build and verification work.

## The project in one paragraph

Two watch faces for my **Garmin Vivoactive 5** (390×390 round AMOLED, touchscreen), installed
as two separate faces: **Day Ring** (a 24-hour day/night bezel with my fasting track and a "now"
needle, three arc gauges, two subdials) and **Halo** (a glowing ring that fills over my 16-hour
fast, heart-rate trend line, three subdials). Style is the main reason for the project; the
data supports a fat-loss goal (16:8 intermittent fasting, active calories, weight). The time is
**Orbitron Black, two-tone: white hour, orange (#FF9F1C) colon + minutes**. Pure black
background, a colour per stat. Display-only (no taps), no seconds.

## Where everything is (all in this repo, branch `claude/focused-mccarthy-ic0fh4`)

- **Spec (the authority):** `docs/superpowers/specs/2026-11-18-garmin-watch-faces-design.md`
- **Plan (12 tasks, follow it):** `docs/superpowers/plans/2026-11-18-garmin-watch-faces.md`
- **Progress ledger + every ruling made so far:** `docs/superpowers/plans/2026-11-18-garmin-watch-faces.progress.md`
- **Handoff notes:** `docs/superpowers/plans/2026-11-18-garmin-watch-faces.HANDOFF.md`
- **Layout reference (source of truth for geometry):** `garmin-watchfaces/mockups/final-faces.html`
  — data-driven; renders six reference states; contains the exact JS of every format rule,
  the fasting/sunrise logic, and an alignment audit. `?face=dayring|halo&state=<name>&layer=full|base`
  renders one bare 390×390 face; no params renders a gallery of all states.
- **What it should look like:** `garmin-watchfaces/mockups/all-states.png` (both faces × six states)
  and `garmin-watchfaces/mockups/reference/<face>-<state>.png` (1:1 renders) with
  `<face>-<state>.json` (audited element boxes and texts).
- **Reference states:** `garmin-watchfaces/mockups/states.json` — `reference` (10:09 Wed 18 Nov),
  `eating` (15:00), `missing` (no HR/weather/sun/weight), `h12single` (12h, 1:05),
  `large` (99,999 steps, 399.9 lb, 104°F…), `midnight` (00:01 Thu 19 Nov).
- **Generated assets (done):**
  - `garmin-watchfaces/common/resources/fonts/` — 20 BMFont fonts + `fonts.xml`
    (Orbitron 65 px for Day Ring, 59 px for Halo, outline `_AOD` versions for always-on, Inter label sizes)
  - `garmin-watchfaces/common/source/FontMetrics.mc` — per-glyph ink extents (for exact vertical centring)
  - `garmin-watchfaces/common/resources/drawables/atlas_*.png` + `common/source/Atlases.mc` —
    glyph atlases for the curved labels (drawn glyph-by-glyph, rotated)
  - `garmin-watchfaces/common/resources/drawables/*.png` + `sprites.xml` — icons (heart, sunrise/sunset,
    9 weather icons at 14 px and 10 px, Halo head glow fast/eat)
  - `garmin-watchfaces/{dayring,halo}/resources/drawables/<face>_base.png` — static art, drawn first
  - `garmin-watchfaces/common/resources/settings/` + `strings/settings_strings.xml` — eating window
    start/end (30-min choices, minutes since midnight, defaults 720/1200) + hidden `refState`
- **Tools:** `garmin-watchfaces/tools/` — `make_fonts.py`, `make_settings.py`, `export_layers.js`
  (Node + Playwright), `compare.py` (simulator screenshot vs reference, ±1 px per element),
  tests in `tools/tests/` (`python3 -m pytest garmin-watchfaces/tools/tests -q` → 24 passed).

## How to continue

1. Read the spec, the plan, the HANDOFF file and the progress ledger (especially every `Ruling:` line).
2. Use the **superpowers:executing-plans** skill (inline execution — I chose "Native"), with
   superpowers:test-driven-development. Restore the ledger first:
   ```
   mkdir -p .superpowers/sdd/2026-11-18-garmin-watch-faces
   cp docs/superpowers/plans/2026-11-18-garmin-watch-faces.progress.md .superpowers/sdd/2026-11-18-garmin-watch-faces/progress.md
   ```
   Tasks 1–5 are complete — don't redo them. Start at **Task 6**.
3. `pip install -r garmin-watchfaces/tools/requirements.txt` (Pillow, numpy, pytest) for compare.py.
   Node + Playwright are only needed if the mockup changes and assets must be re-exported.
4. At the end, run the final whole-branch review on the most capable model at **xhigh** effort,
   then superpowers:finishing-a-development-branch. Don't open a PR unless I ask.

## Task 6 — Mac setup + capability spike (GATE)

Walk me through anything that needs me:
- VS Code + **Monkey C** extension; **Connect IQ SDK Manager** (signed in with my Garmin account),
  latest SDK + **Vivoactive 5** device. Check what's already installed before asking me.
- Developer key:
  `mkdir -p ~/garmin-dev && cd ~/garmin-dev && openssl genrsa -out developer_key.pem 4096 && openssl pkcs8 -topk8 -inform PEM -outform DER -in developer_key.pem -out developer_key.der -nocrypt`

Then build the tiny spike app in `garmin-watchfaces/spike/` and record findings in
`garmin-watchfaces/SPIKE.md`: device id (expected `vivoactive5`) and API level from the SDK's
device `compiler.json`; whether these work on the Vivoactive 5 in the simulator — (1) drawing a
390×390 PNG, (2) an alpha-blended PNG sprite over a coloured arc, (3) a custom BMFont font,
(4) **one atlas glyph drawn with `dc.drawBitmap2` using a sub-rectangle (`:bitmapX/:bitmapY/:bitmapWidth/:bitmapHeight`),
`:tintColor` and a rotating `:transform` (AffineTransform)**, (5) an arc in a colour with alpha
(`Graphics.createColor`); the unit-test command that works (`monkeyc … --unit-test`, then
`monkeydo … -t`); how to set the `refState` property in the simulator; how to get a screenshot of
the watch screen at a known scale (compare.py auto-locates the face at 1× or 2×, or takes `--crop`);
and whether the simulator's AMOLED burn-in check runs in low-power mode.

**GATE:** if any of the five draw tests fails — especially (4), which the curved labels depend
on — stop and bring me options with images via AskUserQuestion before writing more code.
Note: the API names in the plan were written from memory without the SDK; verify them against the
SDK docs/samples and record any differences as rulings.

## Tasks 7–12 (details are in the plan)

7. Shared pure logic + Monkey C unit tests (`Geometry`, `Format`, `Units`, `Fasting`, `Calories`, `Sun`).
   **Add these test cases from the ledger rulings:** `duration(849) == "14H 09M"` (minutes zero-padded
   when hours shown), `windowLabel` pads hours (`"08–16"`), `kilo(10000) == "10K"`,
   `windowLabel(720,1200) == "12–20"`, `windowLabel(750,1200) == "12:30–20:00"`. The JS in
   `final-faces.html` (`F`, `fasting`, `sunNext`, `derive`) is the reference implementation.
8. `Snapshot` (live data + fixtures generated from `states.json` by `tools/make_fixtures.py`),
   `Icons` (weather condition mapping), `Draw` (gradient arcs, ticks, ink-centred text, curved text
   via rotated atlas glyphs — must match the mockup's `ct()`/`ctAt()` semantics exactly).
   **Also port the mockup's fit rules:** Halo subdial values fall back from 11 px to 9 px (font
   `HA_B9`) and labels drop letter-spacing when they don't fit inside the dial; Day Ring weather
   low/high labels drop their `°` when within 1 px of the arc end caps (only happens with 3-digit °F).
   Port the row logic too: "after" groups (sparkline, H/L block, SUNSET label) sit a fixed gap after
   the preceding text; the Halo HR + weather pair is centred as a whole.
9. **Day Ring** app, then 10. **Halo** app — draw order and geometry exactly as in the mockup. For
   each: build the reference build, set `refState` 0–5, screenshot, run
   `python3 garmin-watchfaces/tools/compare.py --face <face> --state <name> --shot <png>` → must be
   `PASS` for all six, plus a 2× visual review of every region (curved labels, arcs, glow, subdial
   insets), plus a clean burn-in check for the always-on screen. Commit the screenshots and compare
   outputs to `garmin-watchfaces/verification/<face>/`. Send me a PNG of the results.
11. Release build, side-load to my watch over USB (macOS needs **OpenMTP** — Garmin uses MTP), check
    on the wrist, then export `.iq` packages for a **private beta upload** (only visible to me) —
    Garmin Connect only shows settings for store-installed apps, and that's how I change the eating
    window from my phone. Verify a settings change applies within a minute without reselecting the
    face. Write `garmin-watchfaces/README.md` with all build/test/install commands.
12. **How-to deck** — a slide deck explaining how to install and switch faces, set the eating
    window, a tour of every element on each face (annotated), the eating vs fasting look, what `--`
    means, data notes (active calories are an estimate from total minus a Mifflin–St Jeor resting
    rate, can differ from Garmin Connect by a few percent; weight comes from my Garmin profile;
    weather needs the phone), the always-on screen, troubleshooting. If you can't make a hosted
    slide deck from this session, make a polished PDF or PPTX instead.

## Key decisions already made (don't change without asking)

- Feature list (all always visible): time, date, next sunrise *or* sunset, fasting state + time left
  + progress ring, heart rate (Day Ring: zone gauge 40–190 bpm; Halo: value + ~4 h trend line),
  steps + goal progress, active/total calories, distance (watch units), **weight always in lb**
  (`grams / 453.592`, one decimal), battery `% · N DAYS`, weather (temp, icon, today's high/low; °C/°F
  follows the watch). 12/24 h follows the watch (24 h zero-pads the hour; 12 h doesn't).
- Eating window default 12:00–20:00 every day; windows crossing midnight must work; start == end
  means "no window" (empty ring, `--` labels). Eating state is shown in **cream #F2E3C6** (I approved).
- Missing data never shows 0: `--`, `--:--`, `--°`, `-- LB`.
- Always-on: time only, Orbitron outline, dimmed (hour #9A9A9A, minutes #B8701A), shifting through
  5 positions by minute.
- Stat colours: HR #FF4D4D, steps #3DD6F5, fasting #FF9F1C, battery #4CD964, weather #FFD60A,
  calories #FF5FA2, sunrise/sunset #FFC247.
- Not in scope: taps, seconds, notifications, Body Battery, stress, sleep, weight goal, calorie
  target, other watch models, public store listing.
