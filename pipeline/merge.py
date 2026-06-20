"""Merge and de-overlap detections from the rule and NER detectors."""

from __future__ import annotations

from typing import List

from .types import Entity


def merge(entities: List[Entity]) -> List[Entity]:
    """Resolve overlapping spans into a non-overlapping set.

    Winners are claimed greedily in this order, so a validated rule detection
    always beats an overlapping NER guess regardless of where each span starts:
      1. higher priority source (rules beat NER)
      2. longer span
      3. earlier start
    Any span overlapping an already-claimed span is dropped.
    Returns the survivors sorted by start offset.
    """
    ordered = sorted(
        entities,
        key=lambda e: (-e.priority, -e.length, e.start),
    )

    kept: List[Entity] = []
    for ent in ordered:
        overlaps = any(
            not (ent.end <= k.start or ent.start >= k.end) for k in kept
        )
        if not overlaps:
            kept.append(ent)
    return sorted(kept, key=lambda e: e.start)
