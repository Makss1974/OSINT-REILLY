"""Offline tests: article text extraction and story outlets for reading."""

import time

from reilly.analytics import signals
from reilly.collectors import fulltext
from reilly.models import Article

LONG = "Сили ППО збили 20 з 25 дронів над Київщиною у ніч на 1 листопада. " * 12

LD_PAGE = ('<html><script type="application/ld+json">{"@graph": [{"@type": "NewsArticle", '
           f'"articleBody": "{LONG}"}}]}}</script><p>menu</p></html>')

ARTICLE_PAGE = ("<html><nav><p>Головна сторінка сайту, розділи, підписка на новини</p></nav>"
                "<article><h1>T</h1><script>var x = 1;</script>"
                f"<p>{LONG}</p><p>коротко</p><aside><p>{'Реклама партнера. ' * 5}</p></aside>"
                "</article></html>")


def test_extract_prefers_json_ld():
    assert fulltext.extract(LD_PAGE).startswith("Сили ППО")


def test_extract_article_paragraphs_without_junk():
    text = fulltext.extract(ARTICLE_PAGE)
    assert "Сили ППО" in text and "var x" not in text
    assert "Головна" not in text and "Реклама" not in text and "коротко" not in text


def test_readable_skips_google_redirects():
    assert fulltext.readable("https://www.pravda.com.ua/news/1/")
    assert not fulltext.readable("https://news.google.com/rss/articles/CBMi")
    assert not fulltext.readable("javascript:alert(1)")


def test_sentences_with_facts():
    got = fulltext.sentences_with_facts("Вступ без чисел, просто загальні слова тут. " + LONG, 2)
    assert len(got) == 2 and all(any(ch.isdigit() for ch in s) for s in got)


def test_read_stories_with_llm(monkeypatch):
    from reilly import llm, reading
    stories = [{"title": "Атака", "url": "https://a.ua/1",
                "members": [{"source": "A", "url": "https://a.ua/1"},
                            {"source": "B", "url": "https://b.ua/1"},
                            {"source": "G", "url": "https://news.google.com/x"}]}]
    monkeypatch.setattr(fulltext, "fetch", lambda url: {"url": url, "chars": 900, "text": LONG})
    monkeypatch.setattr(llm, "enabled", lambda: True)
    answer = ('Ось: {"stories": [{"n": 1, "claims": [{"source": "A", "text": "ППО збила 20 дронів"}],'
              ' "conflicts": [{"point": "кількість дронів", "versions": ["A: 20", "B: 25"]}]},'
              ' {"n": 9, "claims": [{"source": "X", "text": "вигадка"}]}]}')
    monkeypatch.setattr(llm, "chat", lambda *a, **k: answer)
    out = reading.read_stories(stories, "uk")
    assert out["read"] == 2 and out["llm"]
    assert out["claims"] == [{"story": "Атака", "source": "A", "url": "https://a.ua/1",
                              "text": "ППО збила 20 дронів"}]
    assert out["conflicts"][0]["versions"] == ["A: 20", "B: 25"]


def test_story_members_one_per_outlet():
    now = time.time()
    arts = [Article("Атака дронів на Київ уночі", f"https://{h}/a{i}", h, now, "uk", "rss")
            for i, h in enumerate(["a.ua", "b.ua", "a.ua", "c.ua"])]
    story = signals.score_articles(arts, ["дрон", "київ"])["stories"][0]
    assert [m["url"] for m in story["members"]].count("https://a.ua/a2") == 0
    assert len(story["members"]) == 3
