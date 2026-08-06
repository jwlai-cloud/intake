#!/usr/bin/env python3
"""Rehearse the demo against the deployed service, and record what the screen does.

Two jobs:

1. **Choreography reference.** It drives the real UI through the exact beats of
   `docs/demo-script.md` and records a video, so you can watch what the app does
   and when before you have to do it live with a person in the room.
2. **Timing truth.** It prints the wall-clock second at which each item actually
   changes state. Those numbers are what the shot list should be built on —
   model latency drifts, and a script written against guessed timings falls
   apart on the take.

    export INTAKE_KEY=...            # the access code
    uv run --with playwright python demo/rehearse.py            # full run
    uv run --with playwright python demo/rehearse.py --preroll  # just seed a session

The web client must already be running against the deployed service:

    cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
      VITE_CHUNK_MS=8000 npm run dev
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import time

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent
APP = os.environ.get("INTAKE_APP_URL", "http://localhost:5173/")
KEY = os.environ.get("INTAKE_KEY", "")
OUT = ROOT / "rehearsal"

# The live-window turns. Both pre-tested against the deployed adjudicator:
# the first must leave M14 partial, the second must close it.
LIVE_TURNS = [
    "Practitioner: have you had any falls in the last year? "
    "Interviewee: oh, I have had a couple of wobbles.",
    "Practitioner: how many times, and what happened the last one? "
    "Interviewee: three times since Christmas, the last one was in May, "
    "I slipped coming down the stairs.",
    # Declined is the third state, and it is worth showing rather than
    # describing. The template permits a decline on alcohol intake; it does not
    # on falls, and the gate enforces that difference.
    "Practitioner: and can I ask how much you drink in a week? "
    "Interviewee: that is my own business, thank you. Put down that I would "
    "rather not say.",
]


async def states(page) -> dict[str, str]:
    """Item id → state class, read off the rendered list."""
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
    await page.fill("input[placeholder^='Interviewee']", text)
    await page.click("button.mini.confirm:has-text('Send')")


async def watch(page, t0: float, before: dict, label: str, timeout: int = 120) -> dict:
    """Wait for any item to change, and report when — that is the shot timing."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        now = await states(page)
        changed = {k: (before.get(k), v) for k, v in now.items() if before.get(k) != v}
        if changed:
            for item_id, (was, is_) in sorted(changed.items()):
                print(f"  T+{time.monotonic() - t0:5.1f}s  {label}: "
                      f"{item_id} {was or '—'} → {is_}")
            return now
        await page.wait_for_timeout(500)
    print(f"  T+{time.monotonic() - t0:5.1f}s  {label}: NOTHING CHANGED (timed out)")
    return before


async def main(preroll_only: bool) -> None:
    if not KEY:
        raise SystemExit("set INTAKE_KEY to the access code")
    OUT.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        t0 = time.monotonic()

        await page.goto(APP, wait_until="networkidle")
        await page.fill("#accessCode", KEY)
        await page.click("button.mini.confirm")
        await page.click("button.btn:has-text('Community nursing')")
        await page.wait_for_selector(".item", timeout=30000)
        print(f"\nsession open · {await page.locator('.item').count()} required items")

        print("\n--- pre-roll (not filmed: this is the state you start recording from)")
        seen = await states(page)
        for n in (1, 2):
            text = (ROOT / f"preroll-{n}.txt").read_text().strip()
            await send(page, text)
            seen = await watch(page, t0, seen, f"preroll {n}")
        print("  coverage:", await page.locator(".progress strong").inner_text())

        if preroll_only:
            print("\nSession seeded. Leave this browser open, or re-seed before the take.")
            await ctx.close(); await browser.close()
            return

        print("\n--- LIVE WINDOW (this is the part that must be one unedited take)")
        live0 = time.monotonic()
        for n, turn in enumerate(LIVE_TURNS, 1):
            said = time.monotonic() - live0
            print(f"  T+{said:5.1f}s  you say turn {n}")
            await send(page, turn)
            seen = await watch(page, live0, seen, f"turn {n}")
            await page.screenshot(path=OUT / f"live-{n}.png", full_page=True)

        print(f"  T+{time.monotonic() - live0:5.1f}s  click Finish")
        await page.click("button:has-text('Finish')")
        await page.wait_for_selector(".gate-card", timeout=60000)
        outstanding = await page.locator(".gate-item").count()
        print(f"  T+{time.monotonic() - live0:5.1f}s  gate refuses · {outstanding} outstanding")
        await page.screenshot(path=OUT / "gate.png")

        # Escalate everything left — the agent drafts each follow-up itself.
        while await page.locator(".gate-item .resolution button:has-text('Escalate')").count():
            await page.locator(".gate-item .resolution button:has-text('Escalate')").first.click()
            await page.wait_for_timeout(5500)
        await page.wait_for_selector(".report", timeout=120000)
        print(f"  T+{time.monotonic() - live0:5.1f}s  report on screen")
        print(f"\n  LIVE WINDOW TOTAL: {time.monotonic() - live0:.0f}s "
              f"(shot list budgets 145s)")
        await page.screenshot(path=OUT / "report.png", full_page=True)

        await ctx.close()
        await browser.close()
        video = sorted(OUT.glob("*.webm"))
        print(f"\nvideo: {video[-1] if video else 'none'}")
        print(f"stills: {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preroll", action="store_true",
                    help="only seed the session to the state you start filming from")
    asyncio.run(main(ap.parse_args().preroll))
