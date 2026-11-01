"""Optional LLM layer via OpenRouter: query translation and a written
summary of already computed results. The numbers never come from the LLM."""

import json
import logging
import re
from typing import Dict, List

from . import config
from .http import FetchError, get_json, post_json

log = logging.getLogger(__name__)
API = "https://openrouter.ai/api/v1"
MAX_MODEL_TRIES = 8  # free models are often busy (429/503): try the next one
_models: List[str] = []


def enabled() -> bool:
    return bool(config.OPENROUTER_TOKEN)


def _candidates() -> List[str]:
    """Configured model, or free models (busy free models are skipped)."""
    if config.OPENROUTER_MODEL:
        return [config.OPENROUTER_MODEL]
    if not _models:
        data = get_json(f"{API}/models", ttl=86400)
        free = [m["id"] for m in data.get("data", []) if m.get("id", "").endswith(":free")
                and not any(k in m["id"] for k in ("safety", "code", "guard"))]
        if not free:
            raise FetchError("openrouter: no free model found; set OPENROUTER_MODEL")
        known = ("llama", "mistral", "gemma", "qwen", "deepseek", "gpt-oss")
        _models.extend(sorted(free, key=lambda m: not any(k in m for k in known)))
    return _models


ANSWER = re.compile(r"<answer>(.*?)(?:</answer>|$)", re.S)


def chat(system: str, user: str, max_tokens: int = 2500) -> str:
    if not enabled():
        raise FetchError("openrouter: OPENROUTER_API_TOKEN not set")
    system += " Put the final answer between <answer> and </answer>."
    errors = []
    for model in list(_candidates())[:MAX_MODEL_TRIES]:
        try:
            data = post_json(f"{API}/chat/completions", {
                "model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "reasoning": {"effort": "low", "exclude": True},
            }, {"Authorization": f"Bearer {config.OPENROUTER_TOKEN}"})
            content = data["choices"][0]["message"]["content"] or ""
            tagged = ANSWER.findall(content)
            content = tagged[-1] if tagged else content
            if content.strip():
                if model in _models:  # remember the one that answered
                    _models.remove(model)
                    _models.insert(0, model)
                return content.strip()
            errors.append(f"{model}: empty answer")
        except FetchError as exc:
            errors.append(f"{model}: {str(exc)[:80]}")
        except (KeyError, IndexError, TypeError):
            errors.append(f"{model}: unexpected answer")
    raise FetchError("openrouter: " + " | ".join(errors))


def translate_query(topic: str, langs: List[str]) -> Dict[str, str]:
    """Short search queries for each language. Falls back to the original text."""
    text = chat(
        "You turn a research topic into short news search queries (2-4 words, no quotes, "
        "no operators). Answer with JSON only: {\"<lang code>\": \"query\", ...}.",
        f"Languages: {', '.join(langs)}\nTopic: {topic}", max_tokens=1500,
    )
    start, end = text.find("{"), text.rfind("}")
    parsed = json.loads(text[start:end + 1])
    return {lang: str(parsed[lang]).strip() for lang in langs if parsed.get(lang)}


def summarize(topic: str, lang_name: str, facts: str) -> str:
    return chat(
        "You are a cautious intelligence analyst. Write a short assessment (max 200 words) "
        f"in {lang_name} based ONLY on the facts given. Separate observed facts from "
        "inferences, state uncertainty, do not invent numbers or events.",
        f"Topic: {topic}\n\nComputed results:\n{facts}",
    )
