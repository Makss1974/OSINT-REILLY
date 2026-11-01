"""Offline tests: feed parsing, hazard rules, profiles."""

import pytest

from reilly import profiles
from reilly.analytics import hazards as hz
from reilly.analytics import signals
from reilly.collectors import rss

RSS = """<?xml version="1.0" encoding="windows-1251"?>
<rss version="2.0"><channel><title>T</title>
<item><title>Атака дронів на Київ</title><link>https://example.org/a</link>
<pubDate>Sun, 01 Nov 2026 10:00:00 +0200</pubDate>
<description><![CDATA[<p>Сили ППО збили <b>20</b> шахедів</p>]]></description></item>
<item><title>Прогноз погоди</title><link>https://example.org/b</link></item>
</channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Quantum chip record</title>
<link href="https://example.org/q"/><updated>2026-10-30T08:00:00Z</updated>
<summary>New qubit record</summary></entry></feed>"""


def test_rss_parse_and_filter():
    items = rss.parse(RSS, {"name": "Test", "lang": "uk", "tier": 1})
    assert [a.url for a in items] == ["https://example.org/a", "https://example.org/b"]
    assert items[0].tier == 1 and items[0].published
    assert "<" not in items[0].snippet and "шахедів" in items[0].snippet
    assert rss.relevant(items[0], ["дрон", "шахед"])
    assert not rss.relevant(items[1], ["дрон", "шахед"])


def test_atom_parse():
    (a,) = rss.parse(ATOM, {"name": "A"})
    assert a.url == "https://example.org/q" and a.published and "qubit" in a.snippet


def test_weather_rules():
    daily = {"time": ["d1", "d2"], "temperature_2m_max": [35.0, 20.0],
             "temperature_2m_min": [18.0, -21.0], "wind_gusts_10m_max": [45.0, 95.0],
             "precipitation_sum": [0.0, 55.0], "relative_humidity_2m_min": [20.0, 90.0]}
    got = {(a["hazard"], a["date"]): a["level"] for a in hz.weather_alerts("X", daily)}
    assert got[("heat", "d1")] == "WARNING"
    assert got[("frost", "d2")] == "WARNING"
    assert got[("wind", "d2")] == "WARNING"
    assert got[("heavy_rain", "d2")] == "WARNING"
    assert got[("fire_weather", "d1")] == "DANGER"     # hot, RH 20 %, gusts 45
    assert ("fire_weather", "d2") not in got


def test_flood_rules():
    past = [100.0] * 60
    daily = {"time": [f"p{i}" for i in range(60)] + ["f1", "f2", "f3"],
             "river_discharge": past + [150.0, 260.0, 420.0]}
    levels = [a["level"] for a in hz.flood_alerts("X", "R", daily)]
    assert levels == ["WARNING", "DANGER"]
    tiny = {"time": daily["time"], "river_discharge": [1.0] * 60 + [9.0, 9.0, 9.0]}
    assert hz.flood_alerts("X", "R", tiny) == []          # not a real river


def test_kp_and_events():
    kp = hz.kp_alerts([{"time": "2026-11-02 00:00", "kp": 6.3, "observed": "predicted"},
                       {"time": "2026-11-01 00:00", "kp": 8.0, "observed": "observed"}])
    assert [a["level"] for a in kp] == ["WARNING"]
    ev = [{"region": "WORLD", "type": "EQ", "magnitude": 5.1, "date": "d", "title": "small",
           "source": "USGS"},
          {"region": "PL", "type": "EQ", "magnitude": 3.0, "date": "d", "title": "local",
           "source": "USGS"},
          {"region": "WORLD", "type": "TC", "level": "Red", "date": "d", "title": "cyclone",
           "source": "GDACS", "current": True}]
    got = hz.summarize(hz.event_alerts(ev))
    assert got["total"] == 2 and got["alerts"][0]["level"] == "DANGER"


def test_relevance_score_long_vocabulary():
    vocab = [f"слово{i}" for i in range(20)] + ["дрон", "ракет", "фронт"]
    assert signals.relevance_score(vocab, "дрони і ракети на фронті") == 1.0
    assert signals.relevance_score(vocab, "погода сьогодні") == 0.0


@pytest.mark.parametrize("pid", profiles.profile_ids())
def test_profiles_build(pid):
    plan = profiles.build_plan(pid, "uk")
    assert plan.profile == pid and plan.search_queries and plan.keywords
    feeds = {f["id"] for f in profiles.load_feeds().values()}
    assert all(f["id"] in feeds for f in plan.feeds)
    if pid == "hazards":
        assert plan.locations
