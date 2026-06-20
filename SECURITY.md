# Security Policy

This project processes **highly confidential material**. Treat it accordingly.

## Threat model & design guarantees

- **Local only.** Detection and processing run on your machine. The only network
  traffic is to a **local** Ollama instance (loopback `127.0.0.1` or the internal
  Docker network). No case data is ever sent to a third-party/cloud service.
- **Encrypted vaults.** The token→original mapping is stored per case in a vault
  encrypted with a passphrase-derived key (scrypt + Fernet/AES). Without the
  passphrase the mapping cannot be recovered.
- **Secrets stay out of git.** `.env`, `vaults/`, `out/`, and `data/` are
  gitignored. The Docker image never bakes in case data (`.dockerignore`).

## Operator responsibilities

- **Choose a strong passphrase** and store it in a password manager, not in `.env`
  committed anywhere. Prefer the interactive prompt over `ANON_PASSPHRASE` on
  shared machines.
- **Keep the repository private.** Do not publish vaults, outputs, or sample
  documents containing real data.
- **Verify before sharing.** Always run `review` and read the anonymized output —
  unstructured detection (names/orgs) is probabilistic and can miss entities.
- **Air-gap when possible.** After pulling the LLM model once, you can run the
  stack with no internet access.

## Reporting a vulnerability

Please report security issues privately to the repository owner rather than via a
public issue. Do not include any real case data in a report.
