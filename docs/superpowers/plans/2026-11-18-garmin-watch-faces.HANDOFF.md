# Handoff: Garmin watch faces — continue from Task 6 on the Mac

Branch: `claude/focused-mccarthy-ic0fh4`
Plan: `docs/superpowers/plans/2026-11-18-garmin-watch-faces.md`
Spec: `docs/superpowers/specs/2026-11-18-garmin-watch-faces-design.md`
Progress ledger (Tasks 1–5 complete, all rulings so far): `docs/superpowers/plans/2026-11-18-garmin-watch-faces.progress.md`

## State
- Tasks 1–5 (cloud tooling) are done and committed: bitmap fonts, curved-text atlases, settings XML,
  data-driven mockups with six reference states + exported base layers/sprites/reference renders,
  and `garmin-watchfaces/tools/compare.py`. `python3 -m pytest garmin-watchfaces/tools/tests -q` → 24 passed.
- Nothing has been compiled with the Connect IQ SDK yet. Task 6 (capability spike) is a GATE.

## Resume
1. Execution method chosen by the owner: **Native** (inline, superpowers:executing-plans), final
   whole-branch reviewer at **xhigh** effort.
2. Restore the ledger into the plan workspace before starting:
   `mkdir -p .superpowers/sdd/2026-11-18-garmin-watch-faces && cp docs/superpowers/plans/2026-11-18-garmin-watch-faces.progress.md .superpowers/sdd/2026-11-18-garmin-watch-faces/progress.md`
3. Start at Task 6. Its Step 1 (owner setup: VS Code + Monkey C extension, SDK Manager with the
   Vivoactive 5 device, developer key at `~/garmin-dev/developer_key.der`) must be done first.
4. Python tools need `pip install -r garmin-watchfaces/tools/requirements.txt`. Re-exporting the
   mockups (only if the mockup changes) needs Node + Playwright with Chromium.

## Owner's standing requirements
- Alignment must be perfect and re-checked on **every** build: compare.py on all six states for
  both faces, plus a visual review at 2× zoom. Never loosen the tolerance to pass.
- Weight always in lb; everything else follows watch settings. Eating window default 12:00–20:00.
- If the rotated-glyph drawing (curved labels) fails in the spike, stop and bring layout
  alternatives to the owner.
- After the faces are built and installed: make the how-to deck (Task 12).
