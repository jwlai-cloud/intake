#!/usr/bin/env python3
"""Rehearse the demo against the deployed service and record a watchable reference.

The hard part of this demo is not the words, it is knowing what the app does and
*when*, so a person can follow it live with someone answering in real time. So
this drives the real UI through the exact beats of `docs/demo-script.md` and
produces:

- `rehearsal/intake-rehearsal.mp4` — narrated, with a visible cursor, click
  ripples, a caption bar and a running clock. A raw Playwright capture has no
  pointer and no sound, so state appears to change with no visible cause.
- a timing log — the second at which each item actually changes state. The shot
  list is built on these numbers, and model latency drifts, so re-run this the
  morning of the take.

    export INTAKE_KEY=...
    uv run --with playwright python demo/rehearse.py
    uv run --with playwright python demo/rehearse.py --preroll   # just seed
    uv run --with playwright python demo/rehearse.py --no-narrate

Needs the client running against the deployed service:

    cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
      VITE_CHUNK_MS=8000 npm run dev

Narration and mp4 conversion use macOS `say` and ffmpeg; both are skipped with a
warning if missing, and the silent webm is still produced.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import shutil
import subprocess
import time

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent
APP = os.environ.get("INTAKE_APP_URL", "http://localhost:5173/")
KEY = os.environ.get("INTAKE_KEY", "")
OUT = ROOT / "rehearsal"
FINAL = OUT / "intake-rehearsal.mp4"

# Pre-tested against the deployed adjudicator. Between them these three produce
# all three resolution states plus a conditional item appearing.
LIVE_TURNS = [
    ("Practitioner: have you had any falls in the last year? "
     "Interviewee: oh, I have had a couple of wobbles.",
     "Asking about falls. The answer is vague on purpose.",
     "She asks about falls. The answer is: oh, I've had a couple of wobbles."),
    ("Practitioner: how many times, and what happened the last one? "
     "Interviewee: three times since Christmas, the last one was in May, "
     "I slipped coming down the stairs.",
     "Asking the question the agent suggested.",
     "Now the specific answer. Three times, the last in May, on the stairs."),
    ("Practitioner: and can I ask how much you drink in a week? "
     "Interviewee: that is my own business, thank you. Put down that I would "
     "rather not say.",
     "The interviewee declines this one.",
     "This one she declines. Declined is a real resolution, not a gap."),
]


class Recorder:
    """Collects narration lines with the second they should be spoken at."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.lines: list[tuple[float, str]] = []

    def say(self, at: float, text: str) -> None:
        if self.enabled:
            self.lines.append((max(at, 0.0), text))


async def caption(page, text: str, elapsed: float) -> None:
    await page.evaluate("([t, s]) => window.rhCaption && window.rhCaption(t, s)",
                        [text, elapsed])


async def click(page, selector: str) -> None:
    """Move the pointer first, so the injected cursor is visibly where it clicks."""
    el = page.locator(selector).first
    await el.scroll_into_view_if_needed()
    box = await el.bounding_box()
    if box:
        await page.mouse.move(box["x"] + box["width"] / 2,
                              box["y"] + box["height"] / 2, steps=18)
        await page.wait_for_timeout(220)
    await el.click()


async def states(page) -> dict[str, str]:
    return await page.evaluate("""() => {
        const out = {};
        for (const el of document.querySelectorAll('.item')) {
            const id = (el.querySelector('h3')?.textContent || '').split(' ')[0];
            const badge = (el.querySelector('.status')?.textContent || '').trim();
            if (id) out[id] = badge;
        }
        return out;
    }""")


async def send(page, text: str) -> None:
    box = "input[placeholder^='Interviewee']"
    await page.locator(box).first.click()
    await page.fill(box, text)
    await click(page, "button.mini.confirm:has-text('Send')")


async def watch(page, t0: float, before: dict, label: str,
                caption_text: str, timeout: int = 120) -> tuple[dict, list[str]]:
    """Wait for any item to change; report when. That is the shot timing."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        now = await states(page)
        changed = {k: (before.get(k), v) for k, v in now.items() if before.get(k) != v}
        if changed:
            described = []
            for item_id, (was, is_) in sorted(changed.items()):
                print(f"  T+{time.monotonic() - t0:5.1f}s  {label}: "
                      f"{item_id} {was or '—'} → {is_}")
                described.append(f"{item_id} {is_}")
            await caption(page, f"{caption_text} <em>→ {', '.join(described)}</em>",
                          time.monotonic() - t0)
            return now, described
        await caption(page, f"{caption_text} <em>working…</em>",
                      time.monotonic() - t0)
        await page.wait_for_timeout(400)
    print(f"  T+{time.monotonic() - t0:5.1f}s  {label}: NOTHING CHANGED (timed out)")
    return before, []


def narrate(lines: list[tuple[float, str]], video: pathlib.Path,
            out: pathlib.Path) -> pathlib.Path:
    """Speak each line at its timestamp and mux onto the video as mp4."""
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found — leaving the silent webm as-is")
        return video
    if not lines or not shutil.which("say"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                       check=True)
        return out

    tmp = OUT / "narration"
    tmp.mkdir(exist_ok=True)
    clips = []
    for n, (at, text) in enumerate(lines):
        aiff = tmp / f"{n:02d}.aiff"
        subprocess.run(["say", "-v", "Daniel", "-o", str(aiff), text], check=True)
        clips.append((at, aiff))

    inputs, filters, labels = ["-i", str(video)], [], []
    for n, (at, aiff) in enumerate(clips):
        inputs += ["-i", str(aiff)]
        filters.append(f"[{n + 1}:a]adelay={int(at * 1000)}|{int(at * 1000)}[a{n}]")
        labels.append(f"[a{n}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(clips)}:dropout_transition=0,"
                   f"volume={len(clips)}[aout]")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(filters),
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


async def main(preroll_only: bool, do_narrate: bool) -> None:
    if not KEY:
        raise SystemExit("set INTAKE_KEY to the access code")
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    voice = Recorder(do_narrate)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 900},
        )
        await ctx.add_init_script(path=str(ROOT / "overlay.js"))
        page = await ctx.new_page()

        await page.goto(APP, wait_until="networkidle")
        await page.fill("#accessCode", KEY)
        await click(page, "button.mini.confirm")
        await click(page, "button.btn:has-text('Community nursing')")
        await page.wait_for_selector(".item", timeout=30000)

        t0 = time.monotonic()
        await caption(page, "Setting up — this part is not filmed.", 0)
        voice.say(0.5, "Setting up. This part is not filmed.")
        print(f"\nsession open · {await page.locator('.item').count()} required items")

        print("\n--- pre-roll (the state you start recording from)")
        seen = await states(page)
        for n in (1, 2):
            text = (ROOT / f"preroll-{n}.txt").read_text().strip()
            await caption(page, f"Pre-roll {n} of 2 — pasting earlier answers.",
                          time.monotonic() - t0)
            await send(page, text)
            seen, _ = await watch(page, t0, seen, f"preroll {n}",
                                  f"Pre-roll {n} of 2")
        coverage = await page.locator(".progress strong").inner_text()
        print("  coverage:", coverage)
        voice.say(time.monotonic() - t0 + 0.3, f"{coverage}. Now the live part.")

        if preroll_only:
            await ctx.close(); await browser.close()
            print("\nSeeded. Leave the browser open, or re-seed before the take.")
            return

        print("\n--- LIVE WINDOW (one unedited take in the real recording)")
        live0 = time.monotonic()
        for n, (turn, cap, spoken) in enumerate(LIVE_TURNS, 1):
            said = time.monotonic() - live0
            print(f"  T+{said:5.1f}s  turn {n}")
            await caption(page, cap, said)
            voice.say(time.monotonic() - t0, spoken)
            await send(page, turn)
            seen, described = await watch(page, live0, seen, f"turn {n}", cap)
            if n == 1:
                voice.say(time.monotonic() - t0 + 0.2,
                          "Mentioned. Not answered. It says what is still missing.")
            if n == 2:
                voice.say(time.monotonic() - t0 + 0.2,
                          "Now it counts. And a new required item just appeared.")
            await page.screenshot(path=OUT / f"live-{n}.png", full_page=True)

        await caption(page, "Asking for the report.", time.monotonic() - live0)
        voice.say(time.monotonic() - t0, "She asks for the report. It refuses.")
        await click(page, "button:has-text('Finish')")
        await page.wait_for_selector(".gate-card", timeout=60000)
        outstanding = await page.locator(".gate-item").count()
        print(f"  T+{time.monotonic() - live0:5.1f}s  gate refuses · {outstanding} outstanding")
        await caption(page, f"The gate refuses — {outstanding} items outstanding.",
                      time.monotonic() - live0)
        await page.screenshot(path=OUT / "gate.png")
        await page.wait_for_timeout(2500)

        voice.say(time.monotonic() - t0,
                  "Escalating. The agent drafts each follow-up itself and routes it.")
        while await page.locator(".gate-item .resolution button:has-text('Escalate')").count():
            await caption(page, "Escalate — the agent drafts and files the follow-up.",
                          time.monotonic() - live0)
            await click(page, ".gate-item .resolution button:has-text('Escalate')")
            await page.wait_for_timeout(5500)

        await page.wait_for_selector(".report", timeout=120000)
        total = time.monotonic() - live0
        print(f"  T+{total:5.1f}s  report on screen")
        print(f"\n  LIVE WINDOW TOTAL: {total:.0f}s")
        await caption(page, "Report — every item resolved, declined or escalated.", total)
        voice.say(time.monotonic() - t0,
                  "Report. Every required item answered, declined, or escalated.")
        await page.wait_for_timeout(4000)
        await page.screenshot(path=OUT / "report.png", full_page=True)

        await ctx.close()
        await browser.close()

    raw = sorted(OUT.glob("*.webm"))
    if not raw:
        print("no video captured")
        return
    final = narrate(voice.lines, raw[-1], FINAL)
    if final != raw[-1]:
        raw[-1].unlink(missing_ok=True)
    print(f"\nvideo:  {final}")
    print(f"stills: {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preroll", action="store_true", help="only seed the session")
    ap.add_argument("--no-narrate", action="store_true", help="skip the voice track")
    a = ap.parse_args()
    asyncio.run(main(a.preroll, not a.no_narrate))
