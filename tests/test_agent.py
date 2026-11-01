"""Offline tests: task agent plan validation, profile fallback, sources.json editing."""

import json

from reilly import agent, profiles


def test_clean_spec_drops_hallucinations():
    tags = {"war": ["X"], "economy": ["Y"]}
    raw = {"langs": ["uk", "xx", "en"], "queries": {"uk": "енергетика зима", "xx": "q"},
           "feed_tags": ["war", "made_up"], "extras": ["nbu_fx", "secret_db"],
           "assets": ["USDUAH=X", "rm -rf /", "BTC"], "countries": ["ua", "Ukraine"],
           "prior": 7, "asset_direction": "sideways", "polarity": "positive"}
    spec = agent._clean_spec(raw, tags)
    assert spec["langs"] == ["uk", "en"] and set(spec["queries"]) == {"uk"}
    assert spec["feed_tags"] == ["war"] and spec["extras"] == ["nbu_fx"]
    assert spec["assets"] == ["USDUAH=X", "BTC"] and spec["countries"] == ["UA"]
    assert spec["prior"] == 0.95 and spec["asset_direction"] == "auto"
    assert spec["polarity"] == "positive"


def test_heuristic_spec_matches_profiles():
    spec = agent._heuristic_spec("Ракетні атаки і дрони на фронті", agent.feed_tags())
    assert "war" in spec["feed_tags"] and "war_losses" in spec["extras"]
    none = agent._heuristic_spec("zzzz qqqq", agent.feed_tags())
    assert none["feed_tags"] == [] and none["extras"] == []


def test_plan_task_without_llm():
    plan, spec = agent.plan_task("Курс гривні та інфляція в Україні", "uk", 30, use_llm=False)
    assert plan.feeds and "nbu_fx" in plan.extras and not spec["note"]


def test_sources_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"_help": "h", "feeds": {
        "a": {"name": "A", "url": "https://a.example/rss", "lang": "en", "tier": 1,
              "tags": ["war"]}}}), encoding="utf-8")
    monkeypatch.setattr(profiles, "SOURCES_FILE", path)
    fid = profiles.add_feed("Бабель", "https://babel.ua/rss.xml", "uk", 1, ["war"], True)
    assert fid == "babel"
    assert profiles.add_feed("A", "https://other.example/rss", "en", 2, []) == "a_2"
    feeds = profiles.all_feeds()
    feeds["a"]["enabled"] = False
    profiles.save_feeds(feeds)
    assert set(profiles.load_feeds()) == {"babel", "a_2"}
    assert json.loads(path.read_text(encoding="utf-8"))["_help"] == "h"
