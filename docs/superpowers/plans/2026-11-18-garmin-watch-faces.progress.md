# SDD ledger — plan: docs/superpowers/plans/2026-11-18-garmin-watch-faces.md
Spec: docs/superpowers/specs/2026-11-18-garmin-watch-faces-design.md
Workspace: dedicated branch claude/focused-mccarthy-ic0fh4 in an ephemeral cloud container (isolated; no separate worktree needed).
Pre-flight:
- T1→T2: FontSpec/Pillow rendering reused by atlases — consistent.
- T2←T4: atlas special glyphs ♥☀ come from T4 sprites — Ruling: T2 draws ♥/☀ from vector paths directly in Python (same shapes as mockup icons) instead of waiting on T4 sprites — removes the ordering cycle — cost if wrong: glyph shape differs slightly from mockup icon.
- T2←T4: text-widths.json test skipped until T4, re-run in T4 step 6 — consistent.
- T4→T5: reference png/json + base png consumed by compare — consistent.
- T4→T8: states.json consumed by make_fixtures — consistent.
- T1/T2/T3/T7/T8→T9/T10: font ids, atlas ids, properties, module APIs — consistent.
Task 1: Ruling: plan's outline test threshold (<40% of filled pixels) was arbitrary; Orbitron's 2px outline lights 43% while being correctly hollow (inspected) — test now asserts the stroke interior is unlit — cost if wrong: none for rendering; only test semantics changed.
Task 1: complete (commits 70b66a7..95c95bb, tests: python3 -m pytest garmin-watchfaces/tools/tests -q → 5 passed in 0.50s)
Task 2: complete (commits 95c95bb..6cfbd40, tests: python3 -m pytest garmin-watchfaces/tools/tests -q → 10 passed, 1 skipped in 0.58s)
Task 3: complete (commits 6cfbd40..2d1609a, tests: python3 -m pytest garmin-watchfaces/tools/tests -q → 14 passed, 1 skipped in 0.51s)
Task 4: Ruling: duration() zero-pads minutes when hours are shown ("14H 09M") — matches the approved mockup — cost if wrong: none (Task 7 tests must include 849→"14H 09M").
Task 4: Ruling: windowLabel pads hours to 2 digits ("08–16") — consistent with 24h numerals — cost: cosmetic.
Task 4: Ruling: sunrise/sunset unknown → sunset icon, "--:--", label SUNSET — simplest placeholder — cost: cosmetic.
Task 4: Ruling: Halo HR/weather divider is live, not static — the pair re-centres as values change width — cost: none.
Task 4: Ruling: sprites heart_7/sun_8 dropped (atlas draws ♥/☀ itself, see pre-flight); halo head is two sprites (fast/eat) — cost: none.
Task 4: Ruling: base PNG test checks "fully opaque" instead of mode RGB — Playwright writes RGBA PNGs; CIQ accepts either — cost: none.
Task 4: Ruling: Halo subdial values shrink to 9px (new font HA_B9) and labels drop letter-spacing when they don't fit (same corner test in mockup and watch) — audit found "8,888", "99.9K", "100%", "30 DAYS" overflowing in state large — cost: slightly smaller digits for extreme values only.
Task 4: Ruling: ring-clearance audit radius is per face (Day Ring 118 = curved-label baseline; Halo 121 = 4.5px inside the ring's inner edge 125.5) — the 118 rule was Day Ring's geometry — cost if wrong: Halo labels could sit closer to the ring than intended (visual check covers).
Task 4: Ruling: 10px weather icons keep a 1.3px stroke (not 1.5×0.72=1.08px) in mockup and sprites — 1.08px lines rendered faint (fog max alpha 192) — cost: slightly bolder icons than the approved mockup at 10px.
Task 4: Ruling: Day Ring weather low/high labels drop their ° when it would touch the arc end caps (3-digit °F); audit now checks cap clearance (≥1px; 1.5 stripped the approved 14°) — visual review found '109°' touching the cap — cost: no ° on extreme values only.
Task 4: complete (commits 2d1609a..b74d12a, tests: python3 -m pytest garmin-watchfaces/tools/tests -q → 20 passed in 7.29s)
Task 5: complete (commits b74d12a..89d22a9, tests: python3 -m pytest garmin-watchfaces/tools/tests -q → 24 passed in 8.89s)
Task 6: paused at GATE — needs owner's Mac (SDK install + Remote Control folder); no shareable folder available at list time.
