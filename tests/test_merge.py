"""Overlap-resolution tests for merge()."""

from pipeline.merge import merge
from pipeline.types import Entity, SOURCE_RULE, SOURCE_NER


def _rule(start, end, t="BSN"):
    return Entity(start, end, t, "x", SOURCE_RULE, 1.0)


def _ner(start, end, t="LOCATION"):
    return Entity(start, end, t, "x", SOURCE_NER, 0.8)


def test_rule_beats_overlapping_ner_even_if_ner_starts_earlier():
    # NER span "BSN 111222333" (4..17) wraps the rule's digits span (8..17).
    # The validated rule must win; the NER guess is dropped.
    out = merge([_ner(4, 17, "LOCATION"), _rule(8, 17, "BSN")])
    assert len(out) == 1
    assert out[0].source == SOURCE_RULE and out[0].type == "BSN"


def test_non_overlapping_all_kept():
    out = merge([_rule(0, 5), _ner(10, 20), _ner(25, 30)])
    assert len(out) == 3
    assert [e.start for e in out] == [0, 10, 25]


def test_longer_span_wins_within_same_priority():
    out = merge([_ner(0, 5, "PERSON"), _ner(0, 12, "PERSON")])
    assert len(out) == 1
    assert out[0].length == 12


def test_output_sorted_by_start():
    out = merge([_ner(20, 25), _rule(0, 5), _ner(10, 15)])
    assert [e.start for e in out] == [0, 10, 20]
