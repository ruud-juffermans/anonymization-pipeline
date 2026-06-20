"""Shared data types for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# Detection source priorities. Deterministic rules win over probabilistic NER
# when two detections overlap.
SOURCE_RULE = "rule"
SOURCE_NER = "ner"
PRIORITY = {SOURCE_RULE: 2, SOURCE_NER: 1}


@dataclass
class Entity:
    """A detected span of sensitive text within a document."""

    start: int           # char offset, inclusive
    end: int             # char offset, exclusive
    type: str            # canonical type: PERSON, BSN, IBAN, ...
    text: str            # the exact substring detected
    source: str          # SOURCE_RULE or SOURCE_NER
    score: float = 1.0   # confidence (rules = 1.0)

    @property
    def priority(self) -> int:
        return PRIORITY.get(self.source, 0)

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class Detection:
    """A resolved entity that was replaced by a token (for the review report)."""

    token: str
    type: str
    value: str
    start: int
    end: int
    source: str
    score: float


@dataclass
class AnonymizationResult:
    anonymized_text: str
    detections: List[Detection] = field(default_factory=list)
