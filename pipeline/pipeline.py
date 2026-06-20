"""Pipeline orchestration: text -> detect -> tokenize -> result."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import yaml

from . import rules
from .merge import merge
from .ner import build_ner
from .tokenizer import apply, reverse
from .types import AnonymizationResult
from .vault import CaseVault


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


# Sensible defaults so the config resolves even without a .env (e.g. local runs).
_ENV_DEFAULTS = {
    "OLLAMA_HOST": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "qwen2.5:7b-instruct",
    "NER_BACKEND": "ollama",
}


def load_config(path: str | Path | None = None) -> Dict:
    """Load config.yaml, expanding ${VAR} references from the environment."""
    for key, default in _ENV_DEFAULTS.items():
        os.environ.setdefault(key, default)
    raw = Path(path or DEFAULT_CONFIG).read_text(encoding="utf-8")
    return yaml.safe_load(os.path.expandvars(raw))


class Anonymizer:
    """Stateful anonymizer bound to one case vault."""

    def __init__(self, config: Dict, vault: CaseVault):
        self.config = config
        self.vault = vault
        self._ner = None  # lazy: only build when first needed

    @classmethod
    def for_case(cls, case_id: str, passphrase: str,
                 config: Dict | None = None) -> "Anonymizer":
        config = config or load_config()
        vault = CaseVault.open(
            vault_dir=config.get("vault_dir", "vaults"),
            case_id=case_id,
            passphrase=passphrase,
            token_formats=config.get("tokens", {}),
        )
        return cls(config, vault)

    @property
    def ner(self):
        if self._ner is None:
            self._ner = build_ner(self.config.get("ner", {}))
        return self._ner

    def anonymize_text(self, text: str) -> AnonymizationResult:
        ents = rules.detect(text, self.config.get("rules", {}))
        try:
            ents += self.ner(text)
        except Exception as exc:  # NER backend unavailable -> rules only
            print(f"[warn] NER backend failed ({exc}); continuing rules-only.")
        merged = merge(ents)
        anon, detections = apply(text, merged, self.vault)
        return AnonymizationResult(anonymized_text=anon, detections=detections)

    def deanonymize_text(self, text: str) -> str:
        return reverse(text, self.vault)

    def save(self) -> None:
        self.vault.save()
