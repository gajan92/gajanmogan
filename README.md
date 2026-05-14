## Gajan Mogan — Aspiring Python Developer (Cybersecurity Focus)

Transitioning from financial services into technology. Building practical Python skills for security automation with industry-aligned foundations.

### What I’m Doing Now
- Building Python skills for cybersecurity use cases (automation, log parsing, simple network tooling)
- Preparing to tackle CTF challenges and publish write-ups
- Target role: Cybersecurity Analyst (SOC, threat detection, incident response)
- Open to collaboration and entry-level opportunities

### Skills & Tools
- Foundations: Networking fundamentals, Linux, troubleshooting, security mindset
- Python: Scripting, file I/O, regex, data parsing, simple CLIs
- Security Concepts: SIEM basics, log analysis, threat hunting fundamentals
- Certifications:
  - Google IT Support Professional Certificate (Coursera)
  - Google Cybersecurity Professional Certificate (Coursera)

#### Badges
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Cybersecurity](https://img.shields.io/badge/Security-Cybersecurity-2b5b84?style=flat&logo=OWASP&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=flat&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=000)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=flat&logo=gnubash&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-007ACC?style=flat&logo=visualstudiocode&logoColor=white)

### Projects (Planned)
- Python Log Analyzer for SIEM Prep — planned (parse auth and web logs, extract IOCs, basic alerts)
- Async Network Port Scanner — planned (async host/port enumeration with simple reporting)
- Phishing Email Header Analyzer — planned (parse headers, detect anomalies, flag SPF/DKIM failures)
- Packet Sniffer (Scapy) — planned (capture and classify basic traffic patterns for learning)

Repos and write-ups coming soon as I begin building and documenting.

### Learning Roadmap & Progress Tracker
- [x] Complete Google IT Support (Coursera)
- [x] Complete Google Cybersecurity (Coursera)
- [x] Linux and terminal fundamentals
- [x] Git/GitHub basics
- [ ] Python fundamentals (control flow, data structures) — in progress
- [ ] Python for security: file parsing, regex, subprocess, requests — in progress
- [ ] Build 3–5 small security tools in Python
- [ ] Start CTF challenges and publish write-ups
- [ ] Foundations of SOC: SIEM workflows, alert triage, IR basics
- [ ] Apply for entry-level cybersecurity roles

### Career Transition
Pivoting from financial services to cybersecurity/technology, applying analytical skills, risk awareness, and stakeholder communication to security operations and tooling.

### Contact
- LinkedIn: https://www.linkedin.com/in/gajan-mogan
- Email: gajan92@gmail.com

### Quote / Motto
“Security is a journey, not a destination.”

---

## YouTube → Podcast Pipeline

Personal podcast feed from YouTube videos. Share a YouTube URL from iPhone or Mac → audio is extracted → episode appears in Pocket Casts via a custom RSS feed. Zero recurring cost, no server required.

### How it works

1. Share a YouTube URL via the iOS Shortcut below → a GitHub Issue is created with the URL as its title.
2. GitHub Actions extracts the audio, uploads the MP3 to a GitHub Release, updates `feed/feed.xml`, and closes the issue.
3. Pocket Casts (or any podcast client) refreshes and the episode appears — with chapters if the video has them.

Visual-heavy content (tutorials, code-alongs, screencasts) is automatically skipped. Episodes expire after 14 days to keep storage minimal.

### Setup

**1. Enable GitHub Pages**

Settings → Pages → Source: **Deploy from branch** → Branch: `main` → Folder: `/ (root)` → Save.

Feed URL: `https://gajan92.github.io/gajanmogan/feed/feed.xml`

**2. Create a Personal Access Token**

github.com/settings/tokens → Generate new token (classic) → `repo` scope → copy it. This is used by the iOS Shortcut to create issues. The workflow uses the built-in `GITHUB_TOKEN` — no repo secrets needed.

**3. Create the iOS Shortcut**

1. Shortcuts app → **+** → Add Action → **Get Contents of URL**
2. Configure:
   - URL: `https://api.github.com/repos/gajan92/gajanmogan/issues`
   - Method: **POST**
   - Headers: `Authorization: Bearer <your-PAT>` · `Accept: application/vnd.github+json`
   - Request Body: **JSON** → field `title` = **Shortcut Input**
3. Rename to **Send to Podcast** → Settings → enable **Show in Share Sheet**

To use: in YouTube, tap Share → **Send to Podcast**.

**4. Subscribe in Pocket Casts**

Add Podcast → By URL → `https://gajan92.github.io/gajanmogan/feed/feed.xml`

### Customisation

**Allow a channel to bypass the visual-heavy filter** — add the channel name to `data/allowlist.txt` (one per line, case-insensitive) and commit:

```
Lex Fridman Podcast
Huberman Lab
```

**Change retention period** — set `RETENTION_DAYS` env var in the workflow (default: 14 days).

### Dependency updates

`yt-dlp` updates frequently. Check monthly:
```bash
pip install --upgrade yt-dlp && pip freeze | grep yt-dlp
```
Copy the new version into `requirements.txt`.
