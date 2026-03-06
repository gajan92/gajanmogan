# CLAUDE.md — AI Assistant Guide for gajanmogan

This file provides context and conventions for AI assistants (such as Claude Code) working in this repository.

## Repository Overview

This is a **GitHub profile repository** (`gajan92/gajanmogan`). GitHub treats a repository whose name matches the account username as a special profile page — the `README.md` at the root is automatically rendered on the user's public GitHub profile page.

**Owner:** Gajan Mogan
**Purpose:** Personal GitHub profile showcasing background, skills, planned projects, and career transition from financial services into cybersecurity.
**Primary file:** `README.md`

## Repository Structure

```
gajanmogan/
└── README.md        # GitHub profile page — the sole content file
```

There are no source code files, build scripts, tests, or dependencies. This is a pure documentation/markdown repository.

## Content Summary (README.md)

The README presents:

- **Professional bio** — Transitioning from financial services into cybersecurity/tech
- **Current focus** — Python scripting for security automation, CTF prep, SOC fundamentals
- **Target role** — Cybersecurity Analyst (SOC, threat detection, incident response)
- **Skills & Tools** — Python, Linux, Bash, Git/GitHub, networking, SIEM basics
- **Certifications** — Google IT Support, Google Cybersecurity (both Coursera)
- **Planned projects** — Python Log Analyzer, Port Scanner, Phishing Header Analyzer, Packet Sniffer (Scapy)
- **Learning Roadmap** — Checkbox-style progress tracker
- **Contact** — LinkedIn (`https://www.linkedin.com/in/gajan-mogan`), Email (`gajan92@gmail.com`)

## Development Conventions

### Markdown Style
- Use `###` for top-level sections (the repo uses `##` only for the name/title header)
- Badge images use the `https://img.shields.io/badge/...` format with `style=flat`
- Checkboxes in the roadmap use `- [x]` (done) and `- [ ]` (pending)
- Planned projects are noted inline with `— planned` or `— coming soon`

### Tone and Voice
- Professional but approachable; aimed at recruiters and technical collaborators
- First-person is avoided — written in third-person/declarative style
- Avoid hype or overstatement — the profile deliberately sets realistic, honest expectations

### What to Preserve
- Contact details (LinkedIn, email) — do not alter without explicit instruction
- Certification accuracy — only add/remove certs the owner has actually completed
- Project status labels (`planned`, `in progress`) — reflect real status only

## Git Workflow

- The default branch is `master`
- Feature/AI branches follow the pattern `claude/<description>-<id>` (e.g., `claude/add-claude-documentation-KxTP2`)
- Commit messages are written in imperative style (e.g., "Update contact information in README")
- There are no CI/CD pipelines, linters, or automated tests — changes are safe to commit and push directly

## Common Tasks for AI Assistants

| Task | Notes |
|------|-------|
| Update skills or tools | Add to the "Skills & Tools" section; match badge format if adding a new badge |
| Add a project | Use the existing format: `- Project Name — status (brief description)` |
| Update roadmap | Check/uncheck items with `[x]`/`[ ]`; add new items at the bottom of the relevant group |
| Update contact info | Edit the "Contact" section only |
| Refresh bio/summary | Keep tone professional and realistic; avoid overclaiming |

## Out of Scope

- This repo does not contain executable code — do not add build systems, package files, or CI without explicit request
- Do not add a `.gitignore`, `package.json`, `requirements.txt`, or similar unless specifically asked
- Do not restructure the README layout without explicit instruction
