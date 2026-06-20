# Security Policy

This project processes **highly confidential material**. Treat it accordingly.

## Threat model & design guarantees

- **Raw data stays local.** Detection and anonymization run on your machine. Detection
  may use a **local** Ollama instance (loopback `127.0.0.1` or the internal Docker
  network) — the raw document is never sent to a third-party/cloud service. Only the
  anonymized (pseudonymized) output is intended to leave the machine.
- **Encrypted vaults.** The token→original mapping is stored per collection in a vault
  encrypted with a passphrase-derived key (scrypt + Fernet/AES). Without the
  passphrase the mapping cannot be recovered.
- **Secrets stay out of git.** `.env`, `vaults/`, `out/`, and `data/` are
  gitignored. The Docker image never bakes in your documents (`.dockerignore`).

## Operator responsibilities

- **Choose a strong passphrase** and store it in a password manager, not in `.env`
  committed anywhere. Prefer the interactive prompt over `ANON_PASSPHRASE` on
  shared machines.
- **Never publish real data.** Do not commit vaults, outputs, or sample documents
  containing real values.
- **Verify before sharing.** Always run `review` and read the anonymized output —
  unstructured detection (names/orgs) is probabilistic and can miss entities. Treat
  anonymized text as safe to send onward only after this check.
- **Air-gap when possible.** After pulling the LLM model once, you can run the
  stack with no internet access.

## Reporting a vulnerability

Please report security issues privately to the repository owner rather than via a
public issue. Do not include any real confidential data in a report.
