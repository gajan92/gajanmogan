# Garmin watch faces: Day Ring and Halo — design

Date: 2026-11-18
Device: Garmin Vivoactive 5 (390×390 round AMOLED, touchscreen)
Mockups: `garmin-watchfaces/mockups/` (`final-faces.html` is the source of truth for layout;
`face-day-ring.png`, `face-halo.png`, `day-ring-and-halo.png` are renders of it)

## 1. Intent

The owner wants watch faces with a look they can't find in the store — **style is the main
reason**. The look they settled on, after several rounds of mockups and two reference images
(an Apple Watch "instrument" face and a CMF/Nothing face), is rich and detailed, never "simple
and boring": tick-mark bezels, coloured arc gauges, subdials, curved labels, glow, and a bold
techy time font.

The data on the face supports a **fat-loss goal**: a daily 16:8 intermittent fast, how much of
today's calories were *active* calories, and current body weight sit alongside everyday stats.

Two faces are built, and the owner switches between them in the watch's face list:

- **Day Ring** — the whole day lives on the bezel: a 24-hour dial (daylight gold, night navy,
  sunrise/sunset pins), the fasting track inside it, and a "now" needle crossing both.
- **Halo** — the fast is the hero: a glowing ring that burns from deep red to amber as the 16h
  fast progresses, with a heart-rate trend line and three subdials in the centre.

The owner is explicit that **alignment must be perfect** — nothing off-centre, overlapping or
cramped — and that it be **re-checked on every build**, not just once.

## 2. Goals

1. Two separately installable Connect IQ watch faces for the Vivoactive 5, matching the
   mockups in `garmin-watchfaces/mockups/final-faces.html` (layout, colours, sizes).
2. Both show all of these, live:
   | Feature | Shown as |
   |---|---|
   | Time | Orbitron Black (900), two-tone: hour white `#FFFFFF`, colon + minutes orange `#FF9F1C`; 12/24h follows the watch setting; no seconds |
   | Date | e.g. `WED 18 NOV` (Day Ring), `18 WED` (Halo) |
   | Next sunrise **or** sunset | whichever comes next, e.g. `16:31 SUNSET` |
   | Intermittent fasting | state (fasting / eating), time left, progress ring |
   | Heart rate | current bpm; Day Ring: zone gauge (40–190 bpm, blue→red) with marker; Halo: value + trend line of the last ~4h |
   | Steps | count + progress toward the watch's step goal |
   | Calories | active / total, e.g. `640 / 2,180` |
   | Distance today | follows watch units (km or mi), one decimal |
   | Weight | **always in lb**, one decimal, from the Garmin user profile, e.g. `172.8 LB` |
   | Battery | percentage **and** estimated days, e.g. `82% · 6 DAYS` |
   | Weather | current temp + condition icon + today's high/low; °C/°F follows the watch |
3. A per-stat colour system on pure black:
   heart rate `#FF4D4D`, steps `#3DD6F5`, fasting `#FF9F1C`, battery `#4CD964`,
   weather `#FFD60A`, calories `#FF5FA2`, sunrise/sunset `#FFC247`.
4. Settings in the Garmin Connect app (both faces): **eating window start** (default 12:00) and
   **eating window end** (default 20:00). Same window every day.
5. Pixel-accurate alignment, verified automatically and visually on every build (§7).
6. After the faces are built: a slide deck explaining how to install and use them and what
   every element on each face means.

## 3. Non-goals

- Tap actions (the face is display-only by the owner's choice).
- Seconds, notifications, Body Battery, stress, sleep.
- A weight goal or trend; an active-calorie target. (Both offered and declined.)
- Food intake / "calories remaining" — a watch face cannot read MyFitnessPal or similar.
- Other watch models. Vivoactive 6 shares the 390×390 screen, so adding it later should be
  cheap, but it is not built or tested now.
- Publishing to the Connect IQ Store *(builder's call; side-loading is enough for now —
  can be revisited)*.
- Localised labels: fixed labels (`SUNSET`, `STEPS`, `EAT IN`, …) are English
  *(builder's call)*; day/month names come from the watch's own formatting.

## 4. Anti-goals (would be a failure even if it "works")

- Anything visibly misaligned, off-centre, overlapping, clipped by the round edge, or cramped
  against a ring.
- Looking plainer than the mockups (flat colours where the mockup has gradients/glow, missing
  tick scales, a thin or default time font).
- Noticeably worse battery life than a typical stock face.
- Showing wrong or stale numbers without a cue (missing data must show `--`, never `0`).

## 5. Approaches considered

| Approach | Trade-off | Decision |
|---|---|---|
| **A. Native Connect IQ (Monkey C), static art pre-rendered as images, live data drawn in code** | Closest to the mockups (glow, guilloché texture, gradients are baked into images); least redrawing per minute, so best battery. Needs an asset-export step. | **Chosen** by the owner |
| B. Native Connect IQ, everything drawn in code | No image assets, easy to tweak; glow/texture/gradients only approximated; more work per update → more battery. | Rejected |
| C. No-code face builder app | Cannot express the fasting window logic, active-calorie estimate or 24h day ring. | Ruled out |

Packaging: **two separate watch-face apps** (owner's choice over one app with a style
setting). They should share common code (data access, fasting logic, formatting, gauge drawing)
so a fix applies to both — e.g. a `common/` source folder included by each app's
`monkey.jungle` *(builder's call on mechanism)*.

Build & test happen **on the owner's Mac**: Garmin's developer site is not reachable from the
cloud session, and the SDK's device files need the owner's Garmin sign-in. The owner installs
the SDK once; Claude then connects to a project folder on the Mac (with the owner's approval)
to compile, run the simulator, check alignment, and side-load to the watch.

## 6. Behaviour details

### 6.1 Fasting

- Inputs: eating window start `E0` and end `E1` (minutes since midnight, from settings).
  The fast runs from `E1` to the next `E0`. Windows that cross midnight must work
  (e.g. 18:00–02:00) — do all arithmetic modulo 1440.
- **Fasting state** (now outside the window):
  - Progress = elapsed fast / fast length (16h with defaults).
  - Label: `EAT IN 1H 51M` (time until `E0`). Halo also shows `FASTING · 14H 09M / 16H`;
    Day Ring shows `FASTING 88%` on the track.
  - Colours: orange gradient (`#9A2A03 → #FF6A00 → #FF9F1C → #FFCF7A` on Halo;
    `#B23A06 → #FF7A1A → #FFB347` on Day Ring), glowing head.
- **Eating state** (now inside the window) — *builder's call, flagged for the owner to check*:
  - Label: `FAST IN 3H 10M` (time until `E1`).
  - Day Ring: the dotted eating-window segment fills in solid cream `#F2E3C6` up to "now";
    the orange fast track shows empty.
  - Halo: the ring switches to a cream gradient filling over the eating window length, with
    the curved label reading `EATING · 4H 50M / 8H`.
- Time strings: `1H 51M`; under one hour `51M`; exact hours `2H`.

### 6.2 Day Ring specifics (see mockup for exact geometry)

- 24h band at r 172–188: noon at top, midnight at bottom. Night arc navy gradient, daylight
  gold gradient, from today's sunset to sunrise (recomputed daily). Hour separators every hour
  except every 3rd hour, which carries a curved numeral (`00 … 21`).
- Sunrise/sunset pins on the band; "now" needle (white, glowing) from r 158 to r 191.
- Fasting track at r 165 (width 5); eating window as a dotted line; labels `EAT 12–20` (from
  settings) and `FASTING 88%`.
- Inner gauges at r 134 (width 7), mirror-symmetric:
  battery centred at 12 o'clock (fill 0–100%), steps on the right (.11–.33 of the circle,
  capped at 100% but the number keeps counting), heart-rate zone gauge on the left (.67–.89).
  Each has a tick scale at r 141–144 and a curved label at r 119.5.
- Centre column, top to bottom: date, sunset/sunrise row, time, `EAT IN …` pill,
  `4.8 KM • 172.8 LB` row (the dot sits exactly on the centre line).
- Subdials (centres 56 px either side of centre, r 26): calories (ring = active/total) and
  weather (270° gauge from today's low to high with a marker at current temp; icon + value;
  low/high labels inside the open bottom gap).

### 6.3 Halo specifics

- Bezel: minute ticks, 12 hour numerals (12 brighter), chapter ring.
- Guilloché texture: concentric fine rings behind the centre (static image).
- Fasting halo at r 130 (width 9) with blurred glow, 16 hour ticks outside it, white start
  marker at 12 o'clock, glowing head dot at current progress.
- Curved labels between halo and bezel: fasting progress (upper-left), next sunrise/sunset
  (upper-right), `4.8 KM · 172.8 LB` at the bottom with the separator exactly over the 6.
- Centre column: `EAT IN …`, date, time, HR + trend line | weather row (the pair is centred
  as a whole), then three equal subdials 60 px apart: calories, steps, battery.

### 6.4 Data sources and edge cases

| Data | Source (Connect IQ) | When missing |
|---|---|---|
| Heart rate | `Activity.getActivityInfo().currentHeartRate`, else latest `ActivityMonitor` HR sample | `--`, gauge marker hidden |
| HR trend (Halo) | `SensorHistory.getHeartRateHistory` over ~4h, downsampled to ~24 points; refresh ≤ every 5 min | line hidden |
| Steps, goal, distance, total calories | `ActivityMonitor.getInfo()` | `--` |
| Active calories | total − resting estimate. Resting = Mifflin–St Jeor BMR from `UserProfile` (weight, height, age, gender) × (minutes since midnight / 1440); clamp at 0 | show total only |
| Weight | `UserProfile.getProfile().weight` (grams) → lb = g / 453.592 | `-- LB` |
| Battery | `System.getSystemStats().battery`, `.batteryInDays` | days omitted if unavailable |
| Weather | `Weather.getCurrentConditions()` (temp, high, low, condition) | `--°`, icon hidden |
| Sunrise/sunset | `Weather.getSunrise/getSunset` for the weather observation location; cache the last good location in storage | `--:--`; Day Ring band uses the last cached times, or 06:00/18:00 with pins hidden if never known *(builder's call)* |
| Units | `System.getDeviceSettings()` (12/24h, distance, temperature) | — |

The resting-calorie estimate means active calories can differ by a few percent from Garmin
Connect; the how-to deck must say so.

Value ranges the layout must survive: 1-digit and 2-digit hours in 12h mode; steps up to
99,999; calories up to 9,999; weather −40° to 120°F; battery 100%; weight up to 399.9 lb.

### 6.5 Always-on (screen dimmed)

Time only, in Orbitron, dimmed (`#9A9A9A` hour / dimmed orange minutes), within the AMOLED
burn-in rules (low lit-pixel ratio, position shifted slightly each minute). No gauges.

## 7. Alignment verification (every build)

1. **Reference state** in the simulator, matching the mockups: 10:09, Wed 18 Nov, 14h09m into
   a 12:00–20:00 window fast, HR 64, steps 6,412 / 10,000, calories 640 active / 2,180 total,
   4.8 km, 172.8 lb, battery 82% / 6 days, 12° (H 14°, L 6°), sunrise 07:41, sunset 16:31.
2. Screenshot each face from the simulator and **overlay it on the matching mockup render**
   (`face-day-ring.png` / `face-halo.png`, same 390×390 scale). Differences beyond ~1 px in
   element position are fixed, not accepted.
3. Run the automatic checks (the mockup page already does this via `check.js`; the build
   needs an equivalent over the simulator screenshot or the drawing coordinates):
   centred items within 0.75 px of the centre line, no two elements closer than 2 px,
   subdial contents inside the subdial's free radius, centre-column items clear of the
   curved gauge labels.
4. Visual review at 2× zoom of every region, including the edge-case states in §6.4
   (eating state, missing data, 12h single-digit hour, large values, °F).
5. Report results to the owner with each build.

## 8. Decided by the owner

Watch model; style-first purpose; the feature list; steps as count + goal; weather as
temp + icon + high/low; units follow the watch except **weight always in lb**; all features
always visible (no swappable slots); display-only (no taps); battery as % and days; fasting
window 12:00–20:00 every day, shown as state + time left + progress ring; active/total
calories as plain numbers; weight as a plain reminder; pure black background; a colour per
stat; tick bezel, arc gauges, subdials, centred time; Orbitron two-tone time; both Day Ring
and Halo, as two separate faces; pre-rendered-art approach; build on the owner's Mac;
alignment re-checked every build; a how-to deck at the end.

## 9. Left to the builder

- Exact Monkey C structure, shared-code mechanism, and asset export pipeline (render the
  static layers from `final-faces.html` with the dynamic parts removed).
- How gradients on *dynamic* arcs are drawn (segmented arcs vs a pre-rendered gradient ring
  revealed by masking), as long as the result matches the mockup.
- Curved text: use the SDK's radial text drawing if the Vivoactive 5 supports it. **If it does
  not, stop and bring layout alternatives to the owner** — moving curved labels changes the
  look.
- Fonts: Orbitron (time) and Inter (labels) are both SIL Open Font License; convert to
  Connect IQ bitmap fonts at the sizes used.
- Weather condition → icon mapping (about 8 icons in the same line style as the mockup sun).
- Choices marked *(builder's call)* above, which the owner should confirm when reviewing.
