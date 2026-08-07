#!/usr/bin/env python3
"""Drive real traffic through the deployed service so you can film the logs live.

The Google Cloud proof does not have to be captured during the demo — logs are
timestamped records either way. But watching lines arrive is more convincing
than a still, so this exists to make that easy: start your recording, run this,
and real interview traffic hits Cloud Run while the console streams it.

It is deliberately cheap. A run is a handful of chunks, roughly ten cents of
Vertex, and it prints a countdown so you know exactly when to start recording.

    export INTAKE_KEY=...
    uv run python demo/generate-traffic.py             # ~75s of traffic
    uv run python demo/generate-traffic.py --rounds 6  # longer

Have this open first, streaming, zoomed to 150%:
  https://console.cloud.google.com/run/detail/us-central1/intake-agent/logs?project=agent-era
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request

API = os.environ.get("INTAKE_API_BASE",
                     "https://intake-agent-320877670799.us-central1.run.app")
KEY = os.environ.get("INTAKE_KEY", "")

# Each of these routes to different items, so the "chunk routed" log lines vary
# rather than repeating — a log stream that says something different each time
# reads as real work, which is what it is.
TURNS = [
    "Practitioner: have you had any falls in the last year? "
    "Interviewee: oh, I have had a couple of wobbles.",
    "Practitioner: how many times, and what happened the last one? "
    "Interviewee: three times since Christmas, the last was in May on the stairs.",
    "Practitioner: how do you get about indoors? "
    "Interviewee: I use the frame, and my daughter helps me up off the bed.",
    "Practitioner: how has your appetite been? "
    "Interviewee: poor since Christmas, my skirts are hanging off me, maybe a stone.",
    "Practitioner: can I ask how much you drink in a week? "
    "Interviewee: that is my own business, put down that I would rather not say.",
    "Practitioner: what equipment have they put in? "
    "Interviewee: a grab rail by the door and a perching stool in the kitchen.",
]


def api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path, method=method,
        headers={"Content-Type": "application/json", "X-Intake-Key": KEY},
        data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=200) as r:
        return json.loads(r.read())


def main() -> None:
    if not KEY:
        raise SystemExit("set INTAKE_KEY")
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4, help="chunks to send")
    ap.add_argument("--countdown", type=int, default=8,
                    help="seconds before the first request")
    a = ap.parse_args()

    print("\nOpen this, click 'Stream logs', zoom to 150%, start recording:")
    print("  https://console.cloud.google.com/run/detail/us-central1/"
          "intake-agent/logs?project=agent-era\n")
    for n in range(a.countdown, 0, -1):
        print(f"  starting in {n}… ", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")

    session = api("POST", "/sessions", {"template_id": "community-nursing-v1",
                                        "practitioner_id": "console-proof"})
    sid = session["session_id"]
    print(f"session {sid}\n")

    for n, text in enumerate(TURNS[:a.rounds], 1):
        t0 = time.monotonic()
        state = api("POST", f"/sessions/{sid}/chunks", {"seq": n, "text": text})
        touched = [(i["id"], i["state"]) for i in state["items"]
                   if i["state"] != "open"]
        r, req = state["coverage"]["resolved"], state["coverage"]["required"]
        print(f"  chunk {n}  {time.monotonic() - t0:4.1f}s  "
              f"coverage {r}/{req}  {touched[-3:]}")

    print(f"\nDone. Stop recording. The log lines you just filmed are this "
          f"session:\n  {sid}")
    print("\nWorth grabbing while it is fresh:")
    print("  https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/"
          "metrics?project=agent-era")
    print(f"  https://console.cloud.google.com/firestore/databases/intake/data/"
          f"panel/sessions/{sid}?project=agent-era")


if __name__ == "__main__":
    main()
