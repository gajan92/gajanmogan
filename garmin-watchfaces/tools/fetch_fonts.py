"""Download the static TTFs used by the watch faces from Google Fonts (SIL OFL 1.1)."""
import re
import urllib.request
from pathlib import Path

CSS_URL = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"
           "&family=Orbitron:wght@900")
# A non-browser UA makes the CSS API return plain .ttf URLs.
UA = "curl/8"
OUT = Path(__file__).parent / "fonts"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main() -> None:
    css = fetch(CSS_URL).decode()
    blocks = re.findall(r"@font-face\s*{(.*?)}", css, re.S)
    OUT.mkdir(exist_ok=True)
    for b in blocks:
        family = re.search(r"font-family:\s*'([^']+)'", b).group(1)
        weight = re.search(r"font-weight:\s*(\d+)", b).group(1)
        url = re.search(r"url\((https://[^)]+)\) format\(.truetype.\)", b).group(1)
        name = f"{family}-{weight}.ttf"
        (OUT / name).write_bytes(fetch(url))
        print("saved", name)


if __name__ == "__main__":
    main()
