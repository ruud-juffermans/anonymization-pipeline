#!/usr/bin/env python3
"""Measure NER quality on a small labeled Dutch set (synthetic, fake data).

Usage:
    python tools/eval_ner.py                 # uses NER_BACKEND from env/config
    OLLAMA_MODEL=qwen2.5:7b-instruct python tools/eval_ner.py

Reports precision / recall / F1 per entity type so prompt/model changes can be
compared objectively. Matching is on (type, normalized-text), span-agnostic.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline import load_config  # noqa: E402
from pipeline.ner import build_ner          # noqa: E402


# (text, {(TYPE, value), ...}) — fake but realistic Dutch examples.
GOLD = [
    (
        "De overeenkomst tussen Jan de Vries en mevrouw P. Bakker betreft een rekening "
        "bij ABN AMRO en de Rabobank. Het bedrijf Acme Holding B.V. is gevestigd in "
        "Amsterdam aan de Keizersgracht 123. Contactpersoon De Wit werkt vanuit "
        "Rotterdam.",
        {
            ("PERSON", "jan de vries"), ("PERSON", "p. bakker"),
            ("PERSON", "de wit"),
            ("ORG", "abn amro"), ("ORG", "rabobank"),
            ("ORG", "acme holding b.v."),
            ("LOCATION", "amsterdam"), ("LOCATION", "keizersgracht 123"),
            ("LOCATION", "rotterdam"),
        },
    ),
    (
        "Op 3 maart bezocht Fatima El Amrani het kantoor van Stichting Steunfonds "
        "in Utrecht. Zij sprak met directeur Henk Visser over een lening van ING.",
        {
            ("PERSON", "fatima el amrani"), ("PERSON", "henk visser"),
            ("ORG", "stichting steunfonds"), ("ORG", "ing"),
            ("LOCATION", "utrecht"),
        },
    ),
    (
        "Volgens het rapport van Mohammed Ouali vond de levering plaats in Eindhoven, "
        "in een pand van Vastgoed Brabant N.V. aan de Stratumsedijk 45.",
        {
            ("PERSON", "mohammed ouali"),
            ("ORG", "vastgoed brabant n.v."),
            ("LOCATION", "eindhoven"), ("LOCATION", "stratumsedijk 45"),
        },
    ),
]

TYPES = ["PERSON", "ORG", "LOCATION"]


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def main() -> int:
    cfg = load_config()
    ner = build_ner(cfg["ner"])
    print(f"backend={cfg['ner']['backend']} "
          f"model={cfg['ner'].get('ollama', {}).get('model', '-')}\n")

    # counts[type] = [covered_gold, matched_pred, n_pred, n_gold]
    # Matching is containment-aware: a gold entity counts as covered if some
    # predicted span of the same type contains it (or vice versa). This reflects
    # the anonymization goal — over-redacting "mevrouw P. Bakker" still hides the
    # name "P. Bakker", so it should not be scored as a miss.
    counts = {t: [0, 0, 0, 0] for t in TYPES}

    def _hit(a: str, b: str) -> bool:
        return a in b or b in a

    for text, gold in GOLD:
        pred = {(e.type, _norm(e.text)) for e in ner(text)}
        gold_norm = {(t, _norm(v)) for t, v in gold}

        missed, spurious = [], []
        for t in TYPES:
            g = [v for (tp, v) in gold_norm if tp == t]
            p = [v for (tp, v) in pred if tp == t]
            for gv in g:
                if any(_hit(gv, pv) for pv in p):
                    counts[t][0] += 1
                else:
                    missed.append((t, gv))
            for pv in p:
                if any(_hit(gv, pv) for gv in g):
                    counts[t][1] += 1
                else:
                    spurious.append((t, pv))
            counts[t][2] += len(p)
            counts[t][3] += len(g)

        print(f"--- sample ({len(text)} chars) ---")
        if missed:
            print("  MISSED :", sorted(missed))
        if spurious:
            print("  EXTRA  :", sorted(spurious))
        if not missed and not spurious:
            print("  perfect")

    print("\n{:<10} {:>6} {:>6} {:>6}".format("TYPE", "PREC", "REC", "F1"))
    cov = mat = npred = ngold = 0
    for t in TYPES:
        c = counts[t]
        cov += c[0]; mat += c[1]; npred += c[2]; ngold += c[3]
        prec = c[1] / c[2] if c[2] else 0.0
        rec = c[0] / c[3] if c[3] else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        print("{:<10} {:>6.2f} {:>6.2f} {:>6.2f}".format(t, prec, rec, f1))
    prec = mat / npred if npred else 0.0
    rec = cov / ngold if ngold else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print("{:<10} {:>6.2f} {:>6.2f} {:>6.2f}".format("OVERALL", prec, rec, f1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
