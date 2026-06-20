"""Merge and de-overlap detections from the rule and NER detectors."""

from __future__ import annotations

from typing import List

from .types import Entity


def merge(entities: List[Entity]) -> List[Entity]:
    """Resolve overlapping spans.

    Preference order when two spans overlap:
      1. higher priority source (rules beat NER)
      2. longer span
      3. earlier start
    Returns a non-overlapping list sorted by start offset.
    """
    # Sort so the "winner" of any overlap comes first.
    ordered = sorted(
        entities,
        key=lambda e: (e.start, -e.priority, -e.length),
    )

    kept: List[Entity] = []
    occupied_end = -1
    for ent in ordered:
        if ent.start >= occupied_end:
            kept.append(ent)
            occupied_end = ent.end
        else:
            # Overlaps something already kept. Replace the last kept span only
            # if this one strictly wins on priority then length.
            last = kept[-1]
            if (ent.priority, ent.length) > (last.priority, last.length) \
                    and ent.start <= last.start:
                kept[-1] = ent
                occupied_end = ent.end
            # otherwise drop it
    return sorted(kept, key=lambda e: e.start)
