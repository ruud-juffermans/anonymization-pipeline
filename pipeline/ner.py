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
    """Find every occurrence of `value` in `text` and turn it into an Entity.

    Tries an exact match first, then falls back to case-insensitive matching so a
    model that alters casing (e.g. "amsterdam") still anchors to the real span.
    """
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
    if out:
        return out

    # Case-insensitive fallback; keep the document's original substring/offsets.
    low_text, low_val = text.lower(), value.lower()
    start = 0
    while True:
        idx = low_text.find(low_val, start)
        if idx == -1:
            break
        original = text[idx:idx + len(value)]
        out.append(Entity(idx, idx + len(value), etype, original,
                          SOURCE_NER, score * 0.95))
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


_PROMPT = """Je bent een nauwkeurige named-entity-extractie tool voor vertrouwelijke \
Nederlandse documenten.

Extraheer ELKE afzonderlijke entiteit als een APART object. Groepeer nooit meerdere \
namen of een hele zin in één object.

Types:
- PERSON  : de naam van één persoon, bijv. "Jan de Vries", "P. Bakker". Titels of \
functies zoals "mevrouw", "de heer", "directeur" horen NIET bij de naam.
- ORG     : bedrijf, instantie of organisatie, bijv. "ABN AMRO", "Acme Holding B.V.".
- LOCATION: plaats, straat, adres of postcode, bijv. "Amsterdam", "Keizersgracht 123".

Neem exact de tekst over zoals die in het document staat. Verzin niets; alleen wat \
letterlijk voorkomt.

Voorbeeld:
Tekst: "Piet Jansen werkt bij KPN in Den Haag."
Antwoord: {{"entities":[{{"text":"Piet Jansen","type":"PERSON"}},\
{{"text":"KPN","type":"ORG"}},{{"text":"Den Haag","type":"LOCATION"}}]}}

Tekst:
\"\"\"
{text}
\"\"\"
"""

# Ollama structured-output schema: forces an ARRAY of typed entities, so a weak
# model cannot collapse everything into one object.
_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "type": {"type": "string",
                             "enum": ["PERSON", "ORG", "LOCATION"]},
                },
                "required": ["text", "type"],
            },
        }
    },
    "required": ["entities"],
}


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
                "format": _SCHEMA,   # structured output -> array of entities
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
