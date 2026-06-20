"""Per-case, passphrase-encrypted vault.

Holds the token <-> original mapping for one case so tokens stay consistent across
all of the case's documents and can be reversed by an authorized user.

On-disk format:  MAGIC | version | scrypt-salt(16) | Fernet(ciphertext of JSON)
The JSON is never written in clear text.
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"ANONVLT1"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _normalize(value: str, etype: str) -> str:
    """Canonical key for consistency lookups."""
    if etype in {"BSN", "IBAN", "CARD", "PHONE"}:
        return re.sub(r"\s|-", "", value).upper()
    return re.sub(r"\s+", " ", value).strip().lower()


@dataclass
class _State:
    case_id: str
    entities: Dict[str, dict] = field(default_factory=dict)   # token -> {type,value}
    value_index: Dict[str, str] = field(default_factory=dict)  # "TYPE|norm" -> token
    counters: Dict[str, int] = field(default_factory=dict)     # type -> last n


class CaseVault:
    """A loaded, mutable vault for one case. Call save() to persist."""

    def __init__(self, path: Path, passphrase: str, token_formats: Dict[str, str],
                 state: _State):
        self.path = path
        self.passphrase = passphrase
        self.token_formats = token_formats
        self._state = state

    # -- construction --------------------------------------------------------
    @classmethod
    def open(cls, vault_dir: str, case_id: str, passphrase: str,
             token_formats: Dict[str, str]) -> "CaseVault":
        path = Path(vault_dir) / f"{_safe(case_id)}.vault"
        if path.exists():
            state = cls._load(path, passphrase)
            if state.case_id != case_id:
                raise ValueError(
                    f"Vault case id mismatch: file has {state.case_id!r}")
        else:
            state = _State(case_id=case_id)
        return cls(path, passphrase, token_formats, state)

    # -- token assignment ----------------------------------------------------
    def get_or_create_token(self, etype: str, value: str) -> str:
        """Return the stable token for this value, creating it if new."""
        norm = _normalize(value, etype)
        key = f"{etype}|{norm}"
        existing = self._state.value_index.get(key)
        if existing:
            return existing

        n = self._state.counters.get(etype, 0) + 1
        self._state.counters[etype] = n
        fmt = self.token_formats.get(etype, etype + "_{n:03d}")
        token = fmt.format(n=n)

        self._state.entities[token] = {"type": etype, "value": value}
        self._state.value_index[key] = token
        return token

    def original_for(self, token: str) -> Optional[str]:
        entry = self._state.entities.get(token)
        return entry["value"] if entry else None

    def all_tokens(self) -> Dict[str, dict]:
        return dict(self._state.entities)

    # -- persistence ---------------------------------------------------------
    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(16)
        key = _derive_key(self.passphrase, salt)
        payload = json.dumps({
            "case_id": self._state.case_id,
            "entities": self._state.entities,
            "value_index": self._state.value_index,
            "counters": self._state.counters,
        }).encode("utf-8")
        token = Fernet(key).encrypt(payload)
        with open(self.path, "wb") as fh:
            fh.write(MAGIC + salt + token)

    @staticmethod
    def _load(path: Path, passphrase: str) -> _State:
        blob = path.read_bytes()
        if not blob.startswith(MAGIC):
            raise ValueError("Not a valid vault file")
        body = blob[len(MAGIC):]
        salt, ciphertext = body[:16], body[16:]
        key = _derive_key(passphrase, salt)
        try:
            data = json.loads(Fernet(key).decrypt(ciphertext))
        except Exception as exc:  # InvalidToken etc.
            raise ValueError("Wrong passphrase or corrupted vault") from exc
        return _State(
            case_id=data["case_id"],
            entities=data.get("entities", {}),
            value_index=data.get("value_index", {}),
            counters=data.get("counters", {}),
        )


def _safe(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", case_id)
