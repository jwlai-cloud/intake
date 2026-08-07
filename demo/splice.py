#!/usr/bin/env python3
"""Splice Google Cloud console proof into the demo — screenshots or a recording.

The console segment is the one part I cannot capture, since it needs a
signed-in browser. **Screenshots are enough**: each still is held for a few
seconds with a slow push-in, so it reads as a deliberate shot rather than a
freeze. A screen recording works too, if you would rather.

    uv run python demo/splice.py ~/Desktop/run.png ~/Desktop/logs.png ~/Desktop/vertex.png
    uv run python demo/splice.py ~/Desktop/console.mov --keep 20
    uv run python demo/splice.py ~/Desktop/*.png --hold 6 --at 125

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
    ap.add_argument("console", type=pathlib.Path, nargs="+",
                    help="screenshots (png/jpg) and/or one screen recording")
    ap.add_argument("--hold", type=float, default=5.5,
                    help="seconds per screenshot (default 5.5)")
    ap.add_argument("--at", type=float, default=DEFAULT_AT,
                    help=f"insert point in the demo, seconds (default {DEFAULT_AT})")
    ap.add_argument("--keep", type=float, default=DEFAULT_KEEP,
                    help=f"seconds of the recording to use (default {DEFAULT_KEEP})")
    ap.add_argument("--from-start", type=float, default=0.0,
                    help="skip this many seconds of the recording first")
    a = ap.parse_args()

    for f in a.console:
        if not f.exists():
            raise SystemExit(f"no such file: {f}")
    if not BASE.exists():
        raise SystemExit(f"{BASE} missing — run demo/produce.py first")

    w, h = probe(BASE, "width"), probe(BASE, "height")
    LABEL = ("drawtext=text='Deployed on Google Cloud · project agent-era':"
             "fontcolor=white:fontsize=26:box=1:boxcolor=0x123a43@0.92:"
             "boxborderw=16:x=(w-text_w)/2:y=h-96")
    FIT = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x0b1615")

    pieces = []
    for n, src in enumerate(a.console):
        out = BUILD / f"console-{n}.mp4"
        if src.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            frames = int(a.hold * 25)
            # A slow push-in. A still held dead flat reads as a frozen video;
            # 4% of drift over five seconds reads as a deliberate shot.
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src),
                "-t", str(a.hold),
                "-vf", (f"{FIT},zoompan=z='min(1.04,zoom+0.00018)':d={frames}:"
                        f"s={w}x{h}:fps=25,{LABEL}"),
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", str(out)], check=True)
            print(f"  still  {src.name} → {a.hold:.1f}s")
        else:
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", str(a.from_start), "-t", str(a.keep), "-i", str(src),
                "-vf", f"{FIT},fps=25,{LABEL}",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", str(out)], check=True)
            print(f"  clip   {src.name} → {a.keep:.1f}s")
        pieces.append(out)
    print(f"base {w}x{h} · inserting {len(pieces)} piece(s) at {a.at:.0f}s")

    head, tail = BUILD / "part-head.mp4", BUILD / "part-tail.mp4"
    for path, args in ((head, ["-t", str(a.at)]), (tail, ["-ss", str(a.at)])):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args,
                        "-i", str(BASE), "-an", "-vf", "fps=25",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                        "-pix_fmt", "yuv420p", str(path)], check=True)

    listing = BUILD / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n"
                                for p in [head, *pieces, tail]))
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

    for f in (head, tail, listing, *pieces):
        f.unlink(missing_ok=True)
    joined.rename(OUT)
    print(f"\n{OUT}")
    print("Audio is not on this yet — re-run produce.py's mux against it, or "
          "tell me and I will re-lay the narration over the new timeline.")


if __name__ == "__main__":
    main()
