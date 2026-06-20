"""End-to-end round-trip tests using the rules-only backend (no LLM needed)."""

import os

from pipeline.pipeline import Anonymizer

CONFIG = {
    "vault_dir": None,  # set per-test to a tmp path
    "tokens": {
        "BSN": "BSN_{n:03d}", "IBAN": "IBAN_{n:03d}", "EMAIL": "EMAIL_{n:03d}",
        "PHONE": "PHONE_{n:03d}", "CARD": "CARD_{n:03d}",
    },
    "rules": {"bsn": True, "iban": True, "card": True, "phone": True, "email": True},
    "ner": {"backend": "none"},
}


def _cfg(tmp_path):
    cfg = dict(CONFIG)
    cfg["vault_dir"] = str(tmp_path)
    return cfg


def test_roundtrip(tmp_path):
    cfg = _cfg(tmp_path)
    anon = Anonymizer.for_case("CASE-1", "geheim", cfg)
    text = "Verdachte gebruikt NL91ABNA0417164300 en BSN 111222333."
    result = anon.anonymize_text(text)

    assert "NL91ABNA0417164300" not in result.anonymized_text
    assert "111222333" not in result.anonymized_text
    assert "IBAN_001" in result.anonymized_text

    restored = anon.deanonymize_text(result.anonymized_text)
    assert restored == text


def test_consistency_across_documents(tmp_path):
    cfg = _cfg(tmp_path)
    anon = Anonymizer.for_case("CASE-2", "pw", cfg)
    r1 = anon.anonymize_text("rekening NL91ABNA0417164300")
    r2 = anon.anonymize_text("nogmaals NL91 ABNA 0417 1643 00")
    # Same IBAN (even formatted differently) -> same token.
    assert "IBAN_001" in r1.anonymized_text
    assert "IBAN_001" in r2.anonymized_text


def test_persistence_reopen(tmp_path):
    cfg = _cfg(tmp_path)
    a1 = Anonymizer.for_case("CASE-3", "pw", cfg)
    a1.anonymize_text("BSN 111222333").anonymized_text
    a1.save()

    a2 = Anonymizer.for_case("CASE-3", "pw", cfg)
    # Reopened vault keeps the same mapping.
    assert a2.vault.get_or_create_token("BSN", "111222333") == "BSN_001"


def test_wrong_passphrase(tmp_path):
    cfg = _cfg(tmp_path)
    a1 = Anonymizer.for_case("CASE-4", "right", cfg)
    a1.anonymize_text("BSN 111222333")
    a1.save()

    try:
        Anonymizer.for_case("CASE-4", "wrong", cfg)
    except ValueError:
        return
    raise AssertionError("expected wrong passphrase to fail")
