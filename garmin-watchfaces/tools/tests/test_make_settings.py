import xml.etree.ElementTree as ET

import pytest

from make_settings import write_all


@pytest.fixture(scope="module")
def xml(tmp_path_factory):
    out = tmp_path_factory.mktemp("settings")
    write_all(out)
    return {n: ET.parse(out / f"{n}.xml").getroot() for n in ("properties", "settings", "settings_strings")}


def strings(xml):
    return {s.get("id"): s.text for s in xml["settings_strings"]}


def test_each_setting_lists_48_half_hours_in_order(xml):
    s = strings(xml)
    for setting in xml["settings"]:
        entries = setting.find("settingConfig").findall("listEntry")
        assert [int(e.get("value")) for e in entries] == list(range(0, 1440, 30))
        labels = [s[e.text.removeprefix("@Strings.")] for e in entries]
        assert labels[0] == "00:00" and labels[24] == "12:00" and labels[-1] == "23:30"
        assert len(labels) == 48


def test_titles(xml):
    s = strings(xml)
    titles = [s[x.get("title").removeprefix("@Strings.")] for x in xml["settings"]]
    assert titles == ["Eating window starts", "Eating window ends"]


def test_property_defaults_and_hidden_refstate(xml):
    props = {p.get("id"): (p.get("type"), p.text) for p in xml["properties"]}
    assert props == {"eatStart": ("number", "720"), "eatEnd": ("number", "1200"),
                     "refState": ("number", "0")}
    keys = [x.get("propertyKey") for x in xml["settings"]]
    assert keys == ["@Properties.eatStart", "@Properties.eatEnd"]


def test_every_referenced_string_exists(xml):
    s = strings(xml)
    refs = [x.get("title") for x in xml["settings"]]
    refs += [e.text for x in xml["settings"] for e in x.iter("listEntry")]
    assert all(r.removeprefix("@Strings.") in s for r in refs)
