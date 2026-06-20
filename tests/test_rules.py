"""Checksum / detector tests. No external services needed."""

from pipeline import rules


def test_bsn_11proef():
    assert rules.valid_bsn("111222333")     # valid 11-proef
    assert not rules.valid_bsn("123456789")  # fails
    assert not rules.valid_bsn("000000000")
    assert not rules.valid_bsn("12345")


def test_iban_mod97():
    assert rules.valid_iban("NL91ABNA0417164300")    # textbook valid NL IBAN
    assert rules.valid_iban("NL91 ABNA 0417 1643 00")  # spaced
    assert not rules.valid_iban("NL00ABNA0417164300")


def test_luhn():
    assert rules.valid_luhn("4539578763621486")   # valid Visa test number
    assert not rules.valid_luhn("4539578763621487")


def test_detect_structured():
    text = ("BSN 111222333, rekening NL91ABNA0417164300, "
            "kaart 4539 5787 6362 1486, mail jan@politie.nl, tel 06-12345678.")
    found = {e.type for e in rules.detect(text, {})}
    assert {"BSN", "IBAN", "CARD", "EMAIL", "PHONE"} <= found


def test_no_false_bsn():
    # A random 9-digit run that fails the 11-proef must not be flagged.
    text = "ordernummer 123456780 staat open"
    assert not [e for e in rules.detect(text, {}) if e.type == "BSN"]
