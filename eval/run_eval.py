#!/usr/bin/env python3
"""Score the adjudicator against the labelled cases in eval/cases/.

    uv run python run_eval.py             # all cases
    uv run python run_eval.py --item M14  # one item
    uv run python run_eval.py --demo      # only cases used in the demo script

Exits non-zero if any case labelled "insufficient" was marked sufficient.
That is the failure the product exists to prevent: silently ticking an item
that was never really answered.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

LABELS = ["sufficient", "insufficient", "declined"]
CASES = pathlib.Path(__file__).resolve().parent / "cases"


def load_dotenv() -> None:
    """Minimal .env loader — the repo has no runtime dependency on dotenv."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def turns_of(case: dict) -> list[str]:
    return case["turns"] if "turns" in case else [case["utterance"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", help="only cases for this item id, e.g. M14")
    ap.add_argument("--demo", action="store_true", help="only demo-script cases")
    ap.add_argument("--model", default=None, help="override GEMINI_MODEL")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    load_dotenv()
    from intake_agent.adjudicator import DEFAULT_MODEL, adjudicate, get_client
    from intake_agent.template import Template

    model = args.model or DEFAULT_MODEL
    # Build the client up front: constructing it inside worker threads races and
    # a discarded duplicate closes the shared transport out from under the rest.
    client = get_client()

    cases = [json.loads(p.read_text()) for p in sorted(CASES.glob("*.json"))]
    if args.item:
        cases = [c for c in cases if c["item_id"] == args.item]
    if args.demo:
        cases = [c for c in cases if c.get("demo")]
    if not cases:
        print("no cases matched", file=sys.stderr)
        return 2

    print(f"{len(cases)} cases · model {model}\n")

    def run(case: dict):
        try:
            # Item and guidance come from the template, never from the case file:
            # duplicating them per case let two M14 cases drift apart once already.
            item = Template.load(case["template_id"])[case["item_id"]]
            v = adjudicate(item, turns_of(case), model=model, client=client)
            return case, v, None
        except Exception as exc:  # a crashed call must not read as a pass
            return case, None, exc

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run, cases))

    matrix = {t: dict.fromkeys(LABELS, 0) for t in LABELS}
    critical, wrong, errors = [], [], []

    for case, v, exc in results:
        expected = case["label"]
        if exc is not None:
            errors.append((case, exc))
            print(f"ERROR  {case['case_id']}: {exc}")
            continue
        matrix[expected][v.verdict] += 1
        if v.verdict == expected:
            continue
        if expected == "insufficient" and v.verdict == "sufficient":
            critical.append((case, v))
            print(f"CRITICAL  {case['case_id']}: insufficient → sufficient")
        else:
            wrong.append((case, v))
            print(f"miss      {case['case_id']}: {expected} → {v.verdict}")
        print(f"          evidence: {v.evidence!r}")
        print(f"          reason:   {v.reason}")

    scored = sum(sum(row.values()) for row in matrix.values())
    correct = sum(matrix[l][l] for l in LABELS)

    print("\nconfusion matrix  (rows = labelled, cols = predicted)")
    print(f"{'':<14}" + "".join(f"{c:>14}" for c in LABELS))
    for t in LABELS:
        print(f"{t:<14}" + "".join(f"{matrix[t][c]:>14}" for c in LABELS))

    tp = matrix["sufficient"]["sufficient"]
    fp = sum(matrix[t]["sufficient"] for t in LABELS if t != "sufficient")
    labelled_sufficient = sum(matrix["sufficient"].values())
    # "precision 100% on zero cases" is how a totally broken run reads as a
    # perfect one. Report the absence instead.
    precision = f"{tp / (tp + fp):.1%}" if tp + fp else "n/a"
    recall = f"{tp / labelled_sufficient:.1%}" if labelled_sufficient else "n/a"

    pct = f"  ({correct / scored:.1%})" if scored else ""
    print(f"\naccuracy              {correct}/{scored}{pct}")
    print(f"precision(sufficient) {precision}   ← the number that matters")
    print(f"recall(sufficient)    {recall}")
    if errors:
        print(f"errors                {len(errors)}")

    if not scored:
        print("\nFAIL — nothing was scored. Every case errored.")
        return 1
    if critical:
        print(f"\nFAIL — {len(critical)} insufficient answer(s) marked sufficient.")
        return 1
    if errors:
        print(f"\nFAIL — {len(errors)} case(s) errored.")
        return 1
    print(f"\nPASS — no insufficient answer was marked sufficient."
          f" {len(wrong)} non-critical miss(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
