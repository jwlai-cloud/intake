#!/usr/bin/env python3
"""Offline check of the harness gate itself — no model calls.

The one silent failure mode of an eval harness is exiting 0 when it should
exit 1. This pins that: an insufficient case marked sufficient must fail.

    uv run python test_gate.py
"""

import sys

import run_eval
from intake_agent.adjudicator import Verdict


def fake_adjudicate(verdict: str):
    def _adj(item, turns, *, model=None, client=None):
        return Verdict(verdict=verdict, evidence=turns[0], missing=(), reason="stub")
    return _adj


def run(verdict: str, argv: list[str]) -> int:
    run_eval.get_client = lambda: object()
    import intake_agent.adjudicator as adj
    adj.adjudicate = fake_adjudicate(verdict)
    adj.get_client = lambda: object()
    sys.argv = ["run_eval.py", *argv]
    return run_eval.main()


# An always-"sufficient" adjudicator must fail: the insufficient cases are ticked.
assert run("sufficient", ["--item", "M14"]) == 1, "gate let a false tick through"

# An always-"insufficient" adjudicator misses answers, but never falsely ticks —
# annoying, not dangerous, so it passes the gate.
assert run("insufficient", ["--item", "M14"]) == 0, "gate failed on safe misses"

# No cases matched is its own exit code, not a pass.
assert run("sufficient", ["--item", "ZZ99"]) == 2

print("\ngate check OK")
