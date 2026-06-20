"""Deterministic detectors: regex + checksum validation.

These handle the high-risk *structured* identifiers. Every candidate is validated
with its checksum (11-proef, mod-97, Luhn) so false positives stay low and we never
rely on a probabilistic model for exact digits.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

from .types import Entity, SOURCE_RULE


# ---------------------------------------------------------------------------
# Checksum validators
# ---------------------------------------------------------------------------

def valid_bsn(digits: str) -> bool:
    """Dutch BSN 11-proef. Expects 9 digits."""
    if len(digits) != 9 or not digits.isdigit():
        return False
    if digits == "000000000":
        return False
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    total = sum(int(d) * w for d, w in zip(digits, weights))
    return total % 11 == 0


def valid_iban(candidate: str) -> bool:
    """ISO 13616 mod-97 check."""
    iban = re.sub(r"\s+", "", candidate).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{1,30}", iban):
        return False
    # NL IBANs are exactly 18 chars; allow other lengths but bound them.
    if not (15 <= len(iban) <= 34):
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)  # A->10 ... Z->35
    return int(numeric) % 97 == 1


def valid_luhn(digits: str) -> bool:
    """Luhn check for card numbers. Expects 13-19 digits."""
    if not (13 <= len(digits) <= 19) or not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ---------------------------------------------------------------------------
# Candidate patterns
# ---------------------------------------------------------------------------

# Email (RFC-ish, good enough for redaction).
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Dutch phone numbers: +31 / 0031 / 0... with optional spaces, dashes, parens.
RE_PHONE = re.compile(
    r"(?<![\w])(?:(?:\+31|0031)[\s-]?\(?0?\)?|0)(?:\d[\s-]?){8,9}\d(?![\w])"
)

# 9-digit run -> BSN candidate (validated with 11-proef).
RE_BSN = re.compile(r"(?<!\d)\d{9}(?!\d)")

# IBAN candidate: 2 letters, 2 digits, then alnum groups (allow spaces).
RE_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[\s]?[A-Z0-9]{2,4}){2,8}\b")

# Card candidate: 13-19 digits possibly grouped by spaces/dashes.
RE_CARD = re.compile(r"(?<![\d])(?:\d[\s-]?){12,18}\d(?![\d])")


def _scan(text: str, regex: re.Pattern, etype: str,
          validate: Callable[[str], bool] | None = None,
          normalize: Callable[[str], str] = lambda s: s) -> List[Entity]:
    out: List[Entity] = []
    for m in regex.finditer(text):
        raw = m.group()
        if validate is not None and not validate(normalize(raw)):
            continue
        out.append(Entity(m.start(), m.end(), etype, raw, SOURCE_RULE, 1.0))
    return out


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def detect(text: str, cfg: Dict) -> List[Entity]:
    """Run the enabled rule detectors and return all validated matches."""
    enabled = cfg or {}
    ents: List[Entity] = []

    if enabled.get("email", True):
        ents += _scan(text, RE_EMAIL, "EMAIL")
    if enabled.get("iban", True):
        ents += _scan(text, RE_IBAN, "IBAN", valid_iban)
    if enabled.get("bsn", True):
        ents += _scan(text, RE_BSN, "BSN", valid_bsn)
    if enabled.get("card", True):
        ents += _scan(text, RE_CARD, "CARD", valid_luhn, normalize=_digits)
    if enabled.get("phone", True):
        ents += _scan(text, RE_PHONE, "PHONE")

    return ents
