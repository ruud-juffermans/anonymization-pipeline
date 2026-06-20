"""NER backends for unstructured entities (persons, orgs, locations).

Pluggable: `ollama` (local LLM via 127.0.0.1), `spacy` (deterministic Dutch model),
or `none`. Both real backends are imported lazily so the pipeline runs without them.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from .types import Entity, SOURCE_NER


def build_ner(cfg: Dict):
    """Factory: return a callable(text) -> List[Entity] based on config."""
    backend = (cfg or {}).get("backend", "none")
    label_map = (cfg or {}).get("label_map", {})
    if backend == "ollama":
        return OllamaNER(cfg.get("ollama", {}), label_map)
    if backend == "spacy":
        return SpacyNER(cfg.get("spacy", {}), label_map)
    return NullNER()


def _spans_for(text: str, value: str, etype: str, score: float) -> List[Entity]:
    """Find every exact occurrence of `value` and turn it into an Entity."""
    value = value.strip()
    if len(value) < 2:
        return []
    out: List[Entity] = []
    start = 0
    while True:
        idx = text.find(value, start)
        if idx == -1:
            break
        out.append(Entity(idx, idx + len(value), etype, value, SOURCE_NER, score))
        start = idx + len(value)
    return out


class NullNER:
    def __call__(self, text: str) -> List[Entity]:
        return []


class SpacyNER:
    def __init__(self, cfg: Dict, label_map: Dict):
        import spacy  # lazy
        self.nlp = spacy.load(cfg.get("model", "nl_core_news_lg"))
        self.label_map = label_map

    def __call__(self, text: str) -> List[Entity]:
        doc = self.nlp(text)
        out: List[Entity] = []
        for ent in doc.ents:
            etype = self.label_map.get(ent.label_)
            if not etype:
                continue
            out.append(Entity(ent.start_char, ent.end_char, etype,
                              ent.text, SOURCE_NER, 0.85))
        return out


_PROMPT = """Je bent een data-extractietool. Geef ALLEEN geldige JSON terug.
Vind in de onderstaande Nederlandse tekst alle:
- personen (volledige namen van mensen) -> type "PERSON"
- organisaties / bedrijven -> type "ORG"
- locaties en adressen (straat, plaats, postcode) -> type "LOCATION"

Geef een JSON-lijst van objecten met exact deze velden: "text" (de exacte tekst
zoals in het document) en "type". Verzin niets; alleen wat letterlijk voorkomt.

Tekst:
\"\"\"
{text}
\"\"\"

JSON:"""


class OllamaNER:
    """Calls a LOCAL Ollama instance (loopback). No remote calls."""

    def __init__(self, cfg: Dict, label_map: Dict):
        self.host = cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        self.model = cfg.get("model", "qwen2.5:7b-instruct")
        self.timeout = cfg.get("timeout_s", 120)
        self.label_map = label_map

    def __call__(self, text: str) -> List[Entity]:
        import requests  # lazy
        resp = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": _PROMPT.format(text=text),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        items = self._parse(raw)

        out: List[Entity] = []
        seen = set()
        for item in items:
            value = str(item.get("text", "")).strip()
            label = str(item.get("type", "")).strip().upper()
            etype = self.label_map.get(label, label if label in
                                       {"PERSON", "ORG", "LOCATION"} else None)
            if not value or not etype:
                continue
            for ent in _spans_for(text, value, etype, 0.8):
                key = (ent.start, ent.end)
                if key not in seen:
                    seen.add(key)
                    out.append(ent)
        return out

    @staticmethod
    def _parse(raw: str) -> List[Dict]:
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                return []
            try:
                data = json.loads(m.group())
            except json.JSONDecodeError:
                return []
        if isinstance(data, dict):
            # model may wrap the list, e.g. {"entities": [...]}
            for v in data.values():
                if isinstance(v, list):
                    return v
            return []
        return data if isinstance(data, list) else []
