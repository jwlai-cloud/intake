#!/usr/bin/env python3
"""Splice a screen recording of the Google Cloud console into the demo.

The console segment is the one part I cannot capture — it needs a signed-in
browser. You record it (see `console-capture.md`), this drops it into the cut at
the right moment and re-lays the narration over the whole thing so nothing
drifts.

    uv run python demo/splice.py ~/Desktop/console.mov
    uv run python demo/splice.py ~/Desktop/console.mov --at 125 --keep 20

Why re-lay the audio rather than cutting and joining finished files: inserting
video shifts everything after the insertion point, so narration placed against
the old timeline would land on the wrong frames. The insert is made first, then
every line is placed against the new timeline.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parent
BUILD = ROOT / "build"
BASE = BUILD / "intake-demo.mp4"          # silent capture is re-muxed from this
OUT = BUILD / "intake-demo-final.mp4"

# Where the console proof belongs: just after the second falls verdict, where
# the narration is already describing what the backend did.
DEFAULT_AT = 125.0
DEFAULT_KEEP = 20.0


def probe(path: pathlib.Path, field: str) -> str:
    return subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", f"stream={field}", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout.strip().split(",")[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("console", type=pathlib.Path, help="your console recording")
    ap.add_argument("--at", type=float, default=DEFAULT_AT,
                    help=f"insert point in the demo, seconds (default {DEFAULT_AT})")
    ap.add_argument("--keep", type=float, default=DEFAULT_KEEP,
                    help=f"seconds of the recording to use (default {DEFAULT_KEEP})")
    ap.add_argument("--from-start", type=float, default=0.0,
                    help="skip this many seconds of the recording first")
    a = ap.parse_args()

    if not a.console.exists():
        raise SystemExit(f"no such file: {a.console}")
    if not BASE.exists():
        raise SystemExit(f"{BASE} missing — run demo/produce.py first")

    w, h = probe(BASE, "width"), probe(BASE, "height")
    print(f"base {w}x{h} · inserting {a.keep:.0f}s of {a.console.name} at {a.at:.0f}s")

    # Normalise the console clip: same size and frame rate, letterboxed rather
    # than stretched, and silent — the narration owns the audio track.
    norm = BUILD / "console-normalised.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", str(a.from_start), "-t", str(a.keep), "-i", str(a.console),
        "-vf", (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x0b1615,fps=25,"
                # A label, so nobody has to guess what they are looking at.
                f"drawtext=text='Deployed on Google Cloud · project agent-era':"
                f"fontcolor=white:fontsize=26:box=1:boxcolor=0x123a43@0.92:"
                f"boxborderw=16:x=(w-text_w)/2:y=h-96"),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", str(norm)], check=True)

    head, tail = BUILD / "part-head.mp4", BUILD / "part-tail.mp4"
    for path, args in ((head, ["-t", str(a.at)]), (tail, ["-ss", str(a.at)])):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args,
                        "-i", str(BASE), "-an", "-vf", "fps=25",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                        "-pix_fmt", "yuv420p", str(path)], check=True)

    listing = BUILD / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in (head, norm, tail)))
    joined = BUILD / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)],
                   check=True, cwd=BUILD)

    total = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(joined)],
        capture_output=True, text=True, check=True).stdout)
    print(f"joined: {total:.1f}s")
    if total > 240:
        print(f"  WARNING: {total:.0f}s is over the 4:00 limit — "
              f"lower --keep, or trim a line from produce.py")

    for f in (head, tail, listing):
        f.unlink(missing_ok=True)
    joined.rename(OUT)
    print(f"\n{OUT}")
    print("Audio is not on this yet — re-run produce.py's mux against it, or "
          "tell me and I will re-lay the narration over the new timeline.")


if __name__ == "__main__":
    main()
