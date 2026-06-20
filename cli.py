#!/usr/bin/env python3
"""Command-line interface for the anonimization pipeline.

Commands:
  anonymize    Extract + anonymize one or more documents for a case.
  deanonymize  Restore originals in an anonymized text file (needs passphrase).
  review       Print the detection report for what is stored in a case vault.

The passphrase is read interactively (or from $ANON_PASSPHRASE) so it never lands
in your shell history.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from pipeline.ingest import extract_text
from pipeline.pipeline import Anonymizer, load_config


def _passphrase() -> str:
    pw = os.environ.get("ANON_PASSPHRASE")
    if pw:
        return pw
    return getpass.getpass("Vault passphrase: ")


def cmd_anonymize(args) -> int:
    config = load_config(args.config)
    out_dir = Path(args.out or config.get("output_dir", "out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    anon = Anonymizer.for_case(args.case, _passphrase(), config)

    total = 0
    for raw in args.files:
        src = Path(raw)
        if not src.exists():
            print(f"[skip] not found: {src}")
            continue
        try:
            text = extract_text(src)
        except Exception as exc:
            print(f"[skip] {src.name}: {exc}")
            continue

        result = anon.anonymize_text(text)
        total += len(result.detections)

        out_txt = out_dir / f"{src.stem}.anon.txt"
        out_txt.write_text(result.anonymized_text, encoding="utf-8")

        report = out_dir / f"{src.stem}.report.json"
        report.write_text(json.dumps(
            [d.__dict__ for d in result.detections], ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"[ok] {src.name}: {len(result.detections)} entities "
              f"-> {out_txt.name}")

    anon.save()
    print(f"\nDone. {total} detections. Vault updated: {anon.vault.path}")
    return 0


def cmd_deanonymize(args) -> int:
    config = load_config(args.config)
    anon = Anonymizer.for_case(args.case, _passphrase(), config)
    text = Path(args.file).read_text(encoding="utf-8")
    restored = anon.deanonymize_text(text)
    if args.out:
        Path(args.out).write_text(restored, encoding="utf-8")
        print(f"[ok] restored -> {args.out}")
    else:
        sys.stdout.write(restored)
    return 0


def cmd_review(args) -> int:
    config = load_config(args.config)
    anon = Anonymizer.for_case(args.case, _passphrase(), config)
    tokens = anon.vault.all_tokens()
    if not tokens:
        print("Vault is empty.")
        return 0
    width = max(len(t) for t in tokens)
    print(f"{'TOKEN':<{width}}  {'TYPE':<9}  ORIGINAL")
    print("-" * (width + 30))
    for token in sorted(tokens):
        e = tokens[token]
        masked = e["value"] if args.show_values else _mask(e["value"])
        print(f"{token:<{width}}  {e['type']:<9}  {masked}")
    print(f"\n{len(tokens)} entities in case {args.case}.")
    return 0


def _mask(value: str) -> str:
    if len(value) <= 2:
        return "*" * len(value)
    return value[0] + "*" * (len(value) - 2) + value[-1]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Local reversible anonymization pipeline")
    p.add_argument("--config", help="path to config.yaml")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("anonymize", help="anonymize documents")
    a.add_argument("--case", required=True, help="case id")
    a.add_argument("--out", help="output directory")
    a.add_argument("files", nargs="+", help="documents to anonymize")
    a.set_defaults(func=cmd_anonymize)

    d = sub.add_parser("deanonymize", help="restore originals")
    d.add_argument("--case", required=True, help="case id")
    d.add_argument("--out", help="write restored text here (else stdout)")
    d.add_argument("file", help="anonymized .txt file")
    d.set_defaults(func=cmd_deanonymize)

    r = sub.add_parser("review", help="show the vault's detections")
    r.add_argument("--case", required=True, help="case id")
    r.add_argument("--show-values", action="store_true",
                   help="show original values in full (default: masked)")
    r.set_defaults(func=cmd_review)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
