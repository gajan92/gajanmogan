"""Generate the Connect IQ settings resources: the eating window start/end (30-minute
choices, stored as minutes since midnight) and the hidden refState used by reference builds."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_DIR = ROOT / "common" / "resources" / "settings"
STRINGS_DIR = ROOT / "common" / "resources" / "strings"

PROPERTIES = [("eatStart", 720), ("eatEnd", 1200), ("refState", 0)]
SETTINGS = [("eatStart", "EatStartTitle", "Eating window starts"),
            ("eatEnd", "EatEndTitle", "Eating window ends")]
TIMES = list(range(0, 1440, 30))


def time_id(m: int) -> str:
    return f"T{m // 60:02d}{m % 60:02d}"


def write_all(out_dir: Path | None = None) -> None:
    sdir = Path(out_dir) if out_dir else SETTINGS_DIR
    tdir = Path(out_dir) if out_dir else STRINGS_DIR
    sdir.mkdir(parents=True, exist_ok=True)
    tdir.mkdir(parents=True, exist_ok=True)

    props = "\n".join(f'    <property id="{p}" type="number">{v}</property>' for p, v in PROPERTIES)
    (sdir / "properties.xml").write_text(f"<properties>\n{props}\n</properties>\n")

    blocks = []
    for key, title_id, _ in SETTINGS:
        entries = "\n".join(f'            <listEntry value="{m}">@Strings.{time_id(m)}</listEntry>'
                            for m in TIMES)
        blocks.append(f'    <setting propertyKey="@Properties.{key}" title="@Strings.{title_id}">\n'
                      f'        <settingConfig type="list">\n{entries}\n        </settingConfig>\n'
                      f'    </setting>')
    (sdir / "settings.xml").write_text("<settings>\n" + "\n".join(blocks) + "\n</settings>\n")

    rows = [f'    <string id="{tid}">{text}</string>' for _, tid, text in SETTINGS]
    rows += [f'    <string id="{time_id(m)}">{m // 60:02d}:{m % 60:02d}</string>' for m in TIMES]
    (tdir / "settings_strings.xml").write_text("<strings>\n" + "\n".join(rows) + "\n</strings>\n")


if __name__ == "__main__":
    write_all()
    print("wrote settings resources")
