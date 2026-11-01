"""Reading full articles of the top stories.

For each story up to two outlets are read. The LLM turns the texts into
concrete statements (who, what, when, how many) and lists factual
contradictions between outlets. Without an LLM, sentences with numbers and
dates are shown as the likeliest facts and contradictions are not judged.
"""

import json
from typing import Any, Callable, Dict, List, Tuple

from . import llm
from .collectors import fulltext
from .http import FetchError
from .i18n import LANG_NAMES

Progress = Callable[[str], None]
TEXT_FOR_LLM = 2500  # chars per article sent to the model


def _documents(stories: List[Dict[str, Any]], per_story: int,
               progress: Progress) -> Tuple[List[Dict[str, Any]], List[str]]:
    docs, failed = [], []
    for n, story in enumerate(stories, 1):
        got = 0
        for m in story.get("members") or [{"source": "", "url": story["url"]}]:
            if got >= per_story or not fulltext.readable(m["url"]):
                continue
            progress(f"{m['source'] or m['url'][:40]}")
            try:
                page = fulltext.fetch(m["url"])
            except (FetchError, ValueError) as exc:
                failed.append(f"{m['source']}: {str(exc)[:80]}")
                continue
            if page["text"]:
                docs.append({"n": n, "story": story["title"], "source": m["source"],
                             "url": m["url"], "text": page["text"]})
                got += 1
            else:
                failed.append(f"{m['source']}: too little text (paywall / consent page)")
    return docs, failed


def _ask_llm(docs: List[Dict[str, Any]], lang: str) -> Dict[str, Any]:
    body = "\n\n".join(f"[story {d['n']}] [source: {d['source']}]\n{d['text'][:TEXT_FOR_LLM]}"
                       for d in docs)
    text = llm.chat(
        "You extract verifiable statements from news articles. Use only the texts given. "
        f"Write statements in {LANG_NAMES.get(lang, 'English')}. Answer with one JSON object.",
        "Articles:\n\n" + body + "\n\n"
        'Return {"stories": [{"n": <story number>, '
        '"claims": [{"source": "<source>", "text": "who did what, when, where, how many"}], '
        '"conflicts": [{"point": "what they disagree on", '
        '"versions": ["<source A>: version", "<source B>: version"]}]}]}. '
        "Max 4 claims per story, only concrete facts with actors, numbers or dates. "
        "Conflicts only for real factual disagreements (numbers, dates, who, what happened), "
        "not for one outlet simply giving more detail; [] if none.",
        max_tokens=4000)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the answer")
    return json.loads(text[start:end + 1])


def read_stories(stories: List[Dict[str, Any]], lang: str, use_llm: bool = True,
                 progress: Progress = lambda s: None, n_stories: int = 8,
                 per_story: int = 2) -> Dict[str, Any]:
    stories = stories[:n_stories]
    docs, failed = _documents(stories, per_story, progress)
    out: Dict[str, Any] = {"read": len(docs), "stories": len(stories), "failed": failed,
                           "claims": [], "conflicts": [], "llm": False, "note": ""}
    url_of = {(d["n"], d["source"]): d["url"] for d in docs}
    title = {n: s["title"] for n, s in enumerate(stories, 1)}
    if docs and use_llm and llm.enabled():
        progress("LLM: statements")
        try:
            data = _ask_llm(docs, lang)
            for s in data.get("stories", []):
                n = int(s.get("n", 0))
                if n not in title:
                    continue
                for c in s.get("claims", [])[:4]:
                    src = str(c.get("source", ""))
                    out["claims"].append({"story": title[n], "source": src,
                                          "url": url_of.get((n, src), ""),
                                          "text": str(c.get("text", ""))[:400]})
                for c in s.get("conflicts", []):
                    out["conflicts"].append({"story": title[n], "point": str(c.get("point", ""))[:200],
                                             "versions": [str(v)[:300] for v in c.get("versions", [])][:3]})
            out["llm"] = True
        except (FetchError, ValueError, KeyError, TypeError) as exc:
            out["note"] = f"LLM: {str(exc)[:150]}"
    if not out["llm"]:
        for d in docs:
            for sentence in fulltext.sentences_with_facts(d["text"]):
                out["claims"].append({"story": d["story"], "source": d["source"],
                                      "url": d["url"], "text": sentence})
    return out
