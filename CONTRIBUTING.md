# Contributing

Thanks for your interest. A few guidelines specific to this project.

## Golden rule: no real data

**Never** commit, attach, or paste real case material — documents, BSNs, IBANs,
names, vaults, or anonymized outputs. Use synthetic/test data only (the test suite
uses textbook-valid-but-fake numbers).

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest -q
```

## Guidelines

- Keep the pipeline **offline**. Any new component must not make external network
  calls. Local-LLM (loopback) calls are the only exception.
- Structured identifiers (anything with a checksum) belong in `pipeline/rules.py`
  with a validating test in `tests/`.
- New unstructured entity types go through the NER layer (`pipeline/ner.py`).
- Add tests for new detectors and keep `python -m pytest` green.
- Match the existing style: small modules, type hints, short docstrings.

## Pull requests

Describe the change, the entity types affected, and how you tested it. Confirm no
real data is included.
