"""Replace detected entity spans with stable tokens from the vault."""

from __future__ import annotations

import re
from typing import List

from .types import Entity, Detection
from .vault import CaseVault


def apply(text: str, entities: List[Entity], vault: CaseVault):
    """Replace each entity span with its consistent token.

    Returns (anonymized_text, [Detection, ...]). Replacement is done from the end
    of the string backwards so offsets stay valid.
    """
    detections: List[Detection] = []
    out = text
    for ent in sorted(entities, key=lambda e: e.start, reverse=True):
        token = vault.get_or_create_token(ent.type, ent.text)
        out = out[:ent.start] + token + out[ent.end:]
        detections.append(Detection(
            token=token, type=ent.type, value=ent.text,
            start=ent.start, end=ent.end, source=ent.source, score=ent.score,
        ))
    detections.reverse()  # back to document order
    return out, detections


def reverse(text: str, vault: CaseVault) -> str:
    """Replace every known token in `text` with its original value."""
    tokens = vault.all_tokens()
    if not tokens:
        return text
    # Replace longer tokens first to avoid partial-prefix collisions.
    pattern = re.compile("|".join(
        re.escape(t) for t in sorted(tokens, key=len, reverse=True)))
    return pattern.sub(lambda m: tokens[m.group()]["value"], text)
