# Anonimization Pipeline

Local, offline-capable pipeline for **reversible pseudonymization** of confidential
Dutch documents. Built for financial-investigation casework.

Same entity → same token across an entire **case** (e.g. `Jan de Vries → PERSON_001`
in every document of the case). The token→original mapping is stored in a
**passphrase-encrypted vault** that never leaves your machine, so an authorized user
can re-identify later.

> ⚠️ **Confidential data.** This tool handles classified material. Read
> [SECURITY.md](SECURITY.md) before use. Keep your repository **private** and never
> commit real documents, vaults, or outputs.

## Design principles

1. **Nothing leaves the machine.** All detection and processing is local. The only
   network traffic is to a **local** LLM (Ollama on loopback / the compose network).
   The pipeline also runs fully without an LLM (rules + optional spaCy).
2. **Hybrid detection.** High-risk *structured* identifiers (BSN, IBAN, cards) are
   matched by deterministic **regex + checksum** — never by a probabilistic model.
   *Unstructured* entities (names, orgs, addresses) use a local LLM or spaCy NER.
3. **Reversible & consistent.** A per-case vault guarantees stable tokens and allows
   exact reversal with the passphrase.
4. **Human review.** Every detection is reported so you can verify nothing was
   missed before sharing a document.

## Pipeline

```
ingest → extract text → detect → assign consistent tokens → update vault → anonymized text
                        ├─ rules.py : regex + checksum   (BSN, IBAN, card, phone, email)
                        └─ ner.py   : local LLM / spaCy   (person, org, location/address)
```

## Quick start (Docker — recommended)

```bash
make setup                 # create .env from the template (then edit it)
make up                    # build + start the pipeline and a local Ollama
make model                 # pull the local LLM (qwen2.5:7b-instruct) into Ollama
make test                  # run the test suite in the container

# Put documents in ./data, then:
docker compose exec pipeline python cli.py anonymize --case CASE-2026-001 /data/zaak.docx
docker compose exec pipeline python cli.py review      --case CASE-2026-001
docker compose exec pipeline python cli.py deanonymize --case CASE-2026-001 /app/out/zaak.anon.txt
```

Host folders are mounted into the container:

| Host folder | Purpose |
|---|---|
| `./data` | input documents you want to anonymize |
| `./out`  | anonymized text + per-document JSON reports |
| `./vaults` | encrypted per-case vaults |

### macOS / GPU note

Docker Desktop on Mac runs Linux containers **without GPU**, so the in-container
Ollama is CPU-only. For GPU acceleration on Apple Silicon, run **Ollama natively**
on the host instead and point the pipeline at it:

```bash
# host: install Ollama, then `ollama pull qwen2.5:7b-instruct`
# .env:
OLLAMA_HOST=http://host.docker.internal:11434
```

…and remove/ignore the `ollama` service in compose (or just leave it stopped).

## Quick start (local Python, no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download nl_core_news_lg   # optional, if NER_BACKEND=spacy

python cli.py anonymize --case CASE-2026-001 ./data/zaak.docx --out ./out
python cli.py review      --case CASE-2026-001
python cli.py deanonymize --case CASE-2026-001 ./out/zaak.anon.txt
```

## Configuration

- `.env` — runtime settings (`OLLAMA_HOST`, `OLLAMA_MODEL`, `NER_BACKEND`,
  optional `ANON_PASSPHRASE`). Copy from `.env.example`.
- `config.yaml` — entity types, token formats, enabled rule detectors, and the NER
  backend (`ollama` | `spacy` | `none`).

The passphrase is read from `ANON_PASSPHRASE` or prompted interactively, so it never
lands in your shell history.

## What gets detected

| Type | Detector | Validation |
|---|---|---|
| BSN | regex | 11-proef |
| IBAN | regex | mod-97 |
| Card | regex | Luhn |
| Phone, Email | regex | format |
| Person, Org, Location/Address | local LLM / spaCy | — |

The local LLM uses Ollama **structured output** (a JSON schema) so even small models
return a clean array of typed entities. Default model: `qwen2.5:7b-instruct`.

### Measuring NER quality

`tools/eval_ner.py` scores the NER backend against a small labeled Dutch set
(synthetic data) so prompt/model changes can be compared objectively:

```bash
OLLAMA_MODEL=qwen2.5:7b-instruct python tools/eval_ner.py
```

On the bundled set, `qwen2.5:7b-instruct` scores ~0.97 F1 with perfect recall on
person and organisation names (the highest-risk leaks).

## Project layout

```
.
├── cli.py                  # anonymize / deanonymize / review
├── config.yaml             # entity types, token formats, NER backend
├── docker-compose.yml      # pipeline + local Ollama
├── Dockerfile
├── Makefile                # make setup / up / model / test / ...
├── pipeline/
│   ├── ingest.py           # docx, xlsx, pdf, eml, txt → text
│   ├── rules.py            # regex + checksum detectors
│   ├── ner.py              # local LLM / spaCy / none (pluggable)
│   ├── merge.py            # de-overlap detections
│   ├── tokenizer.py        # consistent tokenization + reversal
│   ├── vault.py            # per-case encrypted vault
│   └── pipeline.py         # orchestration
└── tests/                  # checksum + round-trip tests
```

## Security

See [SECURITY.md](SECURITY.md). In short: keep the repo private, use a strong
passphrase, never commit real data, and always review output before sharing.

## License

See [LICENSE](LICENSE).
