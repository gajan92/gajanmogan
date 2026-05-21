#!/usr/bin/env python3
"""
Post success comment and close the issue — runs only after git push succeeds.

Usage:
    python scripts/close_issue.py --issue-number <int> --repo <owner/repo>

Environment:
    GH_TOKEN  GitHub token with issues scope
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from process_url import gh_comment, gh_close_with_label

RESULT_FILE = Path("/tmp/episode_result.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-number", required=True, type=int)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    token = os.environ["GH_TOKEN"]
    result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

    chapters_note = result.get("chapters_note", "")
    gh_comment(
        args.issue_number,
        f"✅ Added: **{result['title']}** ({result['duration_str']})\n\n"
        f"Download: {result['download_url']}{chapters_note}\n"
        f"Expires: {result['expires_at']}",
        args.repo,
        token,
    )
    gh_close_with_label(args.issue_number, "processed", args.repo, token)


if __name__ == "__main__":
    main()
