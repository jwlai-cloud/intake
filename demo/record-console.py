#!/usr/bin/env python3
"""Record the Cloud console while real traffic hits the deployed service.

macOS `screencapture -v` records the display from the command line, so the
whole proof shot can be driven from here: countdown, start recording, push real
interview chunks through Cloud Run, stop, and normalise the file to match the
demo cut.

**It records your entire screen.** Put the console in front, close anything you
would not publish, and check the result before it goes anywhere near a
submission.

    export INTAKE_KEY=...
    uv run python demo/record-console.py                # ~60s
    uv run python demo/record-console.py --rounds 5 --lead 20

Have this in front, streaming, zoomed to 150%:
  https://console.cloud.google.com/run/detail/us-central1/intake-agent/observability/logs?project=agent-era
"""

from __future__ import annotations

import argparse
import pathlib
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "build"
RAW = OUT / "console-raw.mov"
FINAL = OUT / "console-proof.mp4"

sys.path.insert(0, str(ROOT))


def main() -> None:
    import importlib
    gen = importlib.import_module("generate-traffic".replace("-", "_")) \
        if (ROOT / "generate_traffic.py").exists() else None

    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--lead", type=int, default=12,
                    help="seconds to bring the console forward before recording")
    ap.add_argument("--tail", type=float, default=4.0,
                    help="seconds to keep recording after the last chunk")
    ap.add_argument("--display", type=int, default=1,
                    help="which display to record; 1 is the main one. "
                         "`screencapture -D` numbering — on a multi-monitor "
                         "setup, omitting this silently records the wrong "
                         "screen, which is how the first attempt filmed a "
                         "desktop wallpaper")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    RAW.unlink(missing_ok=True)

    print(f"\n  RECORDS DISPLAY {a.display} IN FULL. On that screen: bring the")
    print("  Cloud Run logs to the front, hide the bookmarks bar (Cmd-Shift-B),")
    print("  zoom to 175%, and close anything you would not publish.\n")
    for n in range(a.lead, 0, -1):
        print(f"  recording starts in {n:2d}s … ", end="\r", flush=True)
        time.sleep(1)
    print(" " * 40, end="\r")

    # Fixed duration, not signal-stopped. screencapture -v given an explicit
    # -V writes a complete file on its own; interrupting it with SIGINT
    # produced no file at all — the same lesson as the truncated Playwright
    # capture, which is that a container is only valid once its writer finishes
    # deliberately.
    seconds = int(2.5 + a.rounds * 19 + a.tail)
    rec = subprocess.Popen(["screencapture", "-v", "-D", str(a.display),
                            "-V", str(seconds), str(RAW)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  ● recording {seconds}s\n")
    time.sleep(2.5)

    subprocess.run([sys.executable, str(ROOT / "generate-traffic.py"),
                    "--rounds", str(a.rounds), "--countdown", "1"], check=False)
    print("\n  waiting for the recording to finish…")
    rec.wait(timeout=seconds + 60)
    print("  ■ stopped")

    if not RAW.exists():
        raise SystemExit("no capture produced — check Screen Recording permission")

    # Keep the full screen. Cropping to the log pane happens afterwards, once
    # a frame has been looked at — guessing a crop blind is how you cut the
    # timestamps off the left edge.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(RAW),
                    "-vf", "scale=1920:-2,fps=25", "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", str(FINAL)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", str(FINAL)],
                         capture_output=True, text=True).stdout.strip()
    print(f"\n  {FINAL}  ({float(dur):.0f}s)")
    print("  Watch it before it goes anywhere — it recorded your whole screen.")


if __name__ == "__main__":
    main()
