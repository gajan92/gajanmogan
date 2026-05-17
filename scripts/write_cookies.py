#!/usr/bin/env python3
"""Convert YT_COOKIE_HEADER env var (raw Cookie string) to Netscape cookies.txt."""
import os
import sys

output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/yt_cookies.txt"
header = os.environ.get("YT_COOKIE_HEADER", "").strip()

if not header:
    print("[write_cookies] YT_COOKIE_HEADER is empty, skipping.")
    sys.exit(0)

SECURE_COOKIE_NAMES = {
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "LOGIN_INFO", "SIDCC",
}


def _is_secure(name: str) -> bool:
    if name.startswith("__Secure-") or name.startswith("__Host-"):
        return True
    return name in SECURE_COOKIE_NAMES


lines = ["# Netscape HTTP Cookie File"]
for pair in header.split(";"):
    pair = pair.strip()
    if "=" not in pair:
        continue
    name, _, value = pair.partition("=")
    name = name.strip()
    if not name:
        continue
    secure = "TRUE" if _is_secure(name) else "FALSE"
    lines.append(f".youtube.com\tTRUE\t/\t{secure}\t2147483647\t{name}\t{value}")

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"[write_cookies] Wrote {len(lines) - 1} cookies to {output_path}")
