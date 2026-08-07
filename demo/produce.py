#!/usr/bin/env python3
"""Produce the four-minute demo video.

The first cut failed three ways: the setup got filmed, so it opened on dead air;
narration was placed by wall-clock without measuring clip lengths, so voices
talked over each other; and nothing on screen said why anything mattered.

So the order is inverted. **The audio timeline is authored and measured first,
and the capture is driven from the same clock.** A clip cannot be placed where
it would overlap another — `voices.Timeline` refuses. Every screen is held for
exactly as long as the line spoken over it.

What the viewer sees is a nurse *using* the app during an interview: starting
the recording, reading the question it suggests, keeping a captured quote, being
refused a report, and letting the agent file the follow-up.

Audio into the agent
--------------------
The interview is synthesised, then POSTed as chunks. That is a side channel —
the browser's own microphone is not the source here. The microphone path is real
and separately verified: `docs/fixtures/` holds two recorded chunks that go
through `getUserMedia` → `MediaRecorder` → the API. Driving Chromium's fake
audio device end to end is the next step; it did not capture reliably in this
harness yet, and shipping a demo that claims otherwise would be a lie on camera.

    export INTAKE_KEY=...
    uv run --with playwright python demo/produce.py

Needs the client running:

    cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
      VITE_CHUNK_MS=8000 npm run dev
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import pathlib
import subprocess
import time
import urllib.request
import wave

from playwright.async_api import async_playwright

import voices
from voices import Timeline, synth

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "build"
APP = os.environ.get("INTAKE_APP_URL", "http://localhost:5173")
API = os.environ.get("INTAKE_API_BASE",
                     "https://intake-agent-320877670799.us-central1.run.app")
KEY = os.environ.get("INTAKE_KEY", "")
DIAGRAMS = ROOT.parent / "docs" / "diagrams"
FINAL = OUT / "intake-demo.mp4"
CONSOLE = ROOT / "console-proof.mp4"   # 15s of live Cloud Run logs, streaming

TURNS = [
    {
        "id": "falls-vague",
        "nurse": "Have you had any falls in the last year?",
        "them": "Oh. I've had a couple of wobbles.",
        "caption": "Falls · a vague answer",
        "why": "This is the moment the whole product exists for.",
        "verdict": "Mentioned, not answered. It lists what is still missing.",
        "working": "That chunk is on Cloud Run now. Transcribe, route, then one "
                   "Gemini call per open item — fourteen items, narrowed to the "
                   "two this chunk is about.",
        "expect": "M14",
    },
    {
        "id": "falls-specific",
        "nurse": "How many times, and what happened the last one?",
        "them": "Three times since Christmas. The last one was in May. "
                "I slipped coming down the stairs.",
        "caption": "Asking the question the agent suggested",
        "why": "A count, and the circumstances. Both of them, this time.",
        "verdict": "Now it counts. And a new required item has just appeared.",
        "working": "The guidance asks for two things: a number, and the "
                   "circumstances of the most recent fall. It checks against "
                   "that note, not its own idea of a good answer.",
        "expect": "M14",
    },
    {
        "id": "alcohol-declined",
        "nurse": "And can I ask how much you drink in a week?",
        "them": "That's my own business, thank you. Put down that I'd rather not say.",
        "caption": "A refusal",
        "why": "The form permits a decline here. It does not on falls.",
        "verdict": "Declined is a real resolution, not a blank.",
        "working": "The form marks which items may be declined. Alcohol intake "
                   "is one. Falls is not.",
        "expect": "M24",
    },
]

OPENING = [
    "A community nurse has ninety minutes and a form she is legally required to "
    "complete. She asks about falls, and the answer is: oh, I've had a couple "
    "of wobbles. Every AI scribe ticks that item. It was mentioned. It was "
    "never answered.",
]

ARCHITECTURE = [
    "Every chunk runs one turn of a Google A-D-K pipeline on Cloud Run, and "
    "state lives in Firestore as one slot per required item — never the "
    "transcript. A three-hour interview costs the same per chunk as a "
    "ten-minute one.",
]

CONSOLE_LINES = [
    "This is that request arriving, in Cloud Run, in this project — A-D-K's own "
    "logging naming the model and the Vertex AI backend.",
    "One routing call, then three Gemini calls in parallel, one per open item. "
    "Two came back insufficient, so those items stay open.",
]

CLOSING = [
    "Forty-seven labelled cases, scored against the live service. One hundred "
    "percent precision on sufficient — it has never once ticked an answer a "
    "human labelled insufficient.",
    "Same engine, a different profession, no code changed. Every competitor "
    "ticks on mention. Intake ticks on answered.",  # last line  # closing line
]


def api(method: str, path: str, body: dict | None = None, tries: int = 4) -> dict:
    """One request, retried — a cold Cloud Run instance can 504 on a big chunk."""
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(
            API + path, method=method,
            headers={"Content-Type": "application/json", "X-Intake-Key": KEY},
            data=json.dumps(body).encode() if body else None)
        try:
            with urllib.request.urlopen(req, timeout=200) as r:
                return json.loads(r.read())
        except Exception as exc:
            last = exc
            print(f"     retry {attempt + 1}/{tries} after {type(exc).__name__}")
            time.sleep(5)
    raise last  # type: ignore[misc]


def chunk_wav(turn: dict) -> pathlib.Path:
    """Nurse question + answer as one wav — exactly what the agent is given."""
    out = OUT / f"chunk-{turn['id']}.wav"
    if out.exists():
        return out
    frames = b""
    for part in (synth("nurse", turn["nurse"]), synth("interviewee", turn["them"])):
        with wave.open(str(part), "rb") as w:
            frames += w.readframes(w.getnframes())
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(voices.SAMPLE_RATE)
        w.writeframes(frames)
    return out


def seed_session() -> str:
    """Reach the state we start filming from. Never on camera — filming this was
    the dead air in the first cut."""
    s = api("POST", "/sessions", {"template_id": "community-nursing-v1",
                                  "practitioner_id": "demo"})
    sid = s["session_id"]
    for n in (1, 2):
        s = api("POST", f"/sessions/{sid}/chunks",
                {"seq": n, "text": (ROOT / f"preroll-{n}.txt").read_text().strip()})
    print(f"   seeded {sid} · {s['coverage']['resolved']} of "
          f"{s['coverage']['required']} resolved")
    return sid


def build_evidence(out: pathlib.Path) -> pathlib.Path:
    """Run the eval for real and render its actual stdout as a page."""
    proc = subprocess.run(["uv", "run", "python", "run_eval.py"],
                          cwd=ROOT.parent / "eval", capture_output=True, text=True)
    tail = "\n".join((proc.stdout or proc.stderr).strip().splitlines()[-15:])
    out.write_text("""<!doctype html><meta charset=utf-8>
<style>
 body{margin:0;background:#0b1615;color:#dbeee6;display:grid;place-items:center;
      height:100vh;font:16px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace}
 .t{width:min(1020px,88vw);background:#12302c;border-radius:16px;padding:34px 38px;
    box-shadow:0 26px 70px #000a}
 .c{color:#7fdcbb;margin-bottom:16px}
 pre{margin:0;white-space:pre-wrap}
</style><div class=t><div class=c>$ uv run python run_eval.py</div>
<pre>""" + tail.replace("&", "&amp;").replace("<", "&lt;") + "</pre></div>")
    return out


async def caption(page, text: str, why: str, at: float) -> None:
    await page.evaluate(
        "([t, s]) => window.rhCaption && window.rhCaption(t, s)",
        [f"{text}<em>{why}</em>" if why else text, at])


async def hold(page, until: float, t0: float, text: str, why: str = "") -> None:
    # Paint once before looping: if the deadline has already passed — which is
    # what happens to the closing beat when the capture runs long — the loop
    # body never executes and the bar keeps an empty caption. That is how the
    # previous cut ended on a blank.
    await caption(page, text, why, time.monotonic() - t0)
    while time.monotonic() - t0 < until:
        await caption(page, text, why, time.monotonic() - t0)
        await page.wait_for_timeout(180)


async def move_click(page, selector: str) -> bool:
    """Click with the pointer visibly travelling there first."""
    el = page.locator(selector).first
    if not await el.count():
        return False
    await el.scroll_into_view_if_needed()
    box = await el.bounding_box()
    if box:
        await page.mouse.move(box["x"] + box["width"] / 2,
                              box["y"] + box["height"] / 2, steps=22)
        await page.wait_for_timeout(280)
    await el.click()
    return True


async def item_states(page) -> dict[str, str]:
    return await page.evaluate("""() => Object.fromEntries(
        [...document.querySelectorAll('.item')].map(el => [
          (el.querySelector('h3')?.textContent || '').split(' ')[0],
          (el.querySelector('.status')?.textContent || '').trim()]))""")


async def main() -> None:
    if not KEY:
        raise SystemExit("set INTAKE_KEY")
    OUT.mkdir(exist_ok=True)
    # Stale captures from a crashed run are truncated — Playwright only writes
    # the container header on ctx.close() — and picking one up produces
    # "EBML header parsing failed" from ffmpeg, a long way from the real cause.
    for old in OUT.glob("*.webm"):
        old.unlink()

    print("1. authoring the audio timeline")
    tl, marks = Timeline(), {}
    for line in OPENING:
        tl.append("narrator", line)
    marks["arch"] = tl.end + 0.5
    tl.append("narrator", ARCHITECTURE[0])

    marks["live"] = tl.end + 0.9
    for turn in TURNS:
        turn["q_at"] = tl.append("nurse", turn["nurse"], gap=0.8)
        turn["a_at"] = tl.append("interviewee", turn["them"], gap=0.35)
        turn["post_at"] = tl.end + 0.15
        tl.append("narrator", turn["working"], gap=1.5)
        # Placed inside the wait, not before it. The agent takes ~20s and the
        # previous cut left nine to twelve seconds of that silent.
        tl.append("narrator", turn["why"], gap=3.5)
        # A verdict takes 15-21s on the deployed service. The line announcing it
        # must land *after* that, or the narration claims something the screen
        # has not done — which is exactly what the previous cut did.
        turn["verdict_at"] = tl.append(
            "narrator", turn["verdict"],
            gap=max(1.5, (turn["post_at"] + 24.0) - tl.end))
        turn["done_by"] = tl.end + 1.5
        chunk_wav(turn)

    marks["console"] = tl.end + 0.7
    for line in CONSOLE_LINES:
        tl.append("narrator", line, gap=0.9)
    marks["console_end"] = tl.end + 0.6

    marks["gate"] = tl.end + 0.8
    tl.append("narrator", "She asks for the report. It refuses.", gap=0.6)
    tl.append("narrator", "The agent drafts each follow-up itself and routes it. "
                          "Nothing is ever left silently blank.", gap=3.0)
    marks["close"] = tl.end + 0.8
    for line in CLOSING:
        tl.append("narrator", line, gap=0.7)

    tl.check()
    print(f"   {len(tl.items)} clips · {tl.end:.1f}s total")
    if tl.end > 243:
        raise SystemExit(f"{tl.end:.0f}s exceeds the 4:00 limit")

    # A dark slate the console footage replaces, so the placeholder is never
    # mistaken for the finished cut if a splice is skipped.
    (OUT / "console-slate.html").write_text(
        "<!doctype html><meta charset=utf-8><style>body{margin:0;"
        "background:#0b1615;color:#7fdcbb;display:grid;place-items:center;"
        "height:100vh;font:600 30px ui-monospace,Menlo,monospace}</style>"
        "<div>Cloud Run · live logs</div>")

    print("2. running the eval for real")
    evidence = build_evidence(OUT / "evidence.html")
    print("3. seeding off camera")
    sid = seed_session()
    # The closing beat opens the second vertical as a real session so it lands
    # on that form's item list. Navigating to the landing page instead put the
    # access-code screen on screen as the last thing the viewer sees.
    alt = api("POST", "/sessions", {"template_id": "loss-adjusting-v1",
                                    "practitioner_id": "demo"})["session_id"]

    print("4. capturing")
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            # So "Start recording" actually starts. Without a fake device the
            # click fails and the app correctly shows a permission error on
            # camera — which is what the previous cut filmed.
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
        ])
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["microphone"],
            record_video_dir=str(OUT), record_video_size={"width": 1440, "height": 900})
        await ctx.add_init_script(path=str(ROOT / "overlay.js"))
        # Seed the code before first paint so the access-code screen never
        # appears in the recording.
        await ctx.add_init_script(
            "try { sessionStorage.setItem('intake.accessCode', "
            + json.dumps(KEY) + ") } catch (e) {}")
        page = await ctx.new_page()
        await page.goto(f"{APP}/?session={sid}", wait_until="networkidle")
        await page.wait_for_selector(".item", timeout=30000)

        # A silently absent overlay is how the first cut ended up with no
        # cursor and no captions: every call site guarded with `&&`, so nothing
        # complained. Check once, loudly.
        if not await page.evaluate("() => typeof window.rhCaption === 'function'"):
            raise SystemExit("overlay.js did not load — captions and cursor would "
                             "be missing from the whole video")

        t0 = time.monotonic()
        loop = asyncio.get_running_loop()
        pending: list[asyncio.Future] = []

        await hold(page, marks["arch"], t0, "Mentioned is not answered",
                   "A required item, discussed, and still blank.")

        await page.goto(f"file://{DIAGRAMS}/intake-architecture.html")
        await hold(page, marks["arch"] + 8, t0, "One ADK turn per chunk",
                   "transcribe → route → adjudicate → coach · Cloud Run + Vertex AI")
        await page.goto(f"file://{DIAGRAMS}/intake-sequence.html")
        await hold(page, marks["live"], t0, "One isolated call per open item",
                   "A wrong verdict cannot spread. Every item is separately scored.")

        await page.goto(f"{APP}/?session={sid}", wait_until="networkidle")
        await page.wait_for_selector(".item", timeout=30000)
        cov = await page.locator(".progress strong").inner_text()
        await caption(page, "Part-way through the visit", cov, time.monotonic() - t0)
        await move_click(page, "button:has-text('Start recording')")
        seen = await item_states(page)

        for n, turn in enumerate(TURNS, 10):
            await hold(page, turn["a_at"], t0, turn["caption"], f"“{turn['nurse']}”")
            await hold(page, turn["post_at"], t0, turn["caption"], f"“{turn['them']}”")
            b64 = base64.b64encode(chunk_wav(turn).read_bytes()).decode()
            pending.append(loop.run_in_executor(
                None, lambda s=n, a=b64: api("POST", f"/sessions/{sid}/chunks",
                                             {"seq": s, "audio_b64": a,
                                              "mime_type": "audio/wav"})))

            changed = None
            while time.monotonic() - t0 < turn["verdict_at"] - 0.5:
                now = await item_states(page)
                diff = [k for k, v in now.items() if seen.get(k) != v]
                if diff:
                    changed = turn["expect"] if turn["expect"] in diff else diff[0]
                    seen = now
                    await page.evaluate("id => window.rhHighlight && window.rhHighlight(id)", changed)
                    print(f"   T+{time.monotonic() - t0:5.1f}s  {changed} → {now[changed]}")
                    break
                await caption(page, turn["caption"], "the agent is judging it now…",
                              time.monotonic() - t0)
                await page.wait_for_timeout(400)

            state = (await item_states(page)).get(changed or turn["expect"], "")
            await hold(page, turn["done_by"], t0,
                       f"{turn['expect']} · {state.upper()}", turn["verdict"])
            await page.evaluate("() => window.rhClearHighlight && window.rhClearHighlight()")
            # She keeps the quote the agent proposed: a real interaction, and it
            # shows the agent proposing rather than deciding.
            if n == 11:
                await move_click(page, ".highlight .mini.confirm")

        # A placeholder held for exactly the console segment's length. The real
        # footage is spliced over this window afterwards; holding the app here
        # would waste the beat, and cutting in blind would drift.
        await page.goto(f"file://{OUT / 'console-slate.html'}")
        await hold(page, marks["console_end"], t0,
                   "Cloud Run · live logs",
                   "ADK naming the model · the call to aiplatform · three "
                   "Gemini calls in parallel")
        await page.goto(f"{APP}/?session={sid}", wait_until="networkidle")
        await page.wait_for_selector(".item", timeout=30000)

        await hold(page, marks["gate"] - 0.8, t0, "Asking for the report", "")
        await move_click(page, "button:has-text('Finish')")
        await page.wait_for_selector(".gate-card", timeout=60000)
        n_out = await page.locator(".gate-item").count()
        await hold(page, marks["gate"] + 9, t0, f"Refused · {n_out} outstanding",
                   "A router, not a wall: ask now, record a decline, or escalate.")
        while await page.locator(".gate-item .resolution button:has-text('Escalate')").count():
            await move_click(page, ".gate-item .resolution button:has-text('Escalate')")
            await page.wait_for_timeout(4500)
        await page.wait_for_selector(".report", timeout=120000)
        await page.evaluate("() => window.scrollTo({top: 1e5, behavior: 'smooth'})")
        await hold(page, marks["close"], t0, "Report",
                   "Every required item answered, declined, or escalated.")

        await page.goto(f"file://{evidence}")
        await hold(page, marks["close"] + 22, t0, "Measured, not asserted",
                   "47 labelled cases · scored against the live service")
        await page.goto(f"{APP}/?session={alt}", wait_until="networkidle")
        await page.wait_for_selector(".item", timeout=30000)
        await hold(page, tl.end + 2.5, t0, "Same engine, different profession",
                   "Loss adjusting · no code changed — the vertical is a JSON template.")
        await page.wait_for_timeout(3000)

        for f in pending:
            try:
                await asyncio.wait_for(f, timeout=5)
            except Exception:
                pass
        await ctx.close()
        await browser.close()

    # Newest by mtime, not alphabetically last.
    # The proof screenshots are easiest to take immediately after a run, when
    # the logs on screen *are* the run that was just filmed. Print a console
    # link already filtered to this session so it is one click, not a hunt.
    import urllib.parse
    q = urllib.parse.quote(
        f'resource.type="cloud_run_revision"\n'
        f'resource.labels.service_name="intake-agent"\n'
        f'textPayload:"{sid}" OR textPayload:"chunk routed"')
    print("\n   Cloud proof — screenshot these now, while the logs are this run:")
    print(f"     logs   https://console.cloud.google.com/logs/query;query={q}"
          f"?project=agent-era")
    print(f"     run    https://console.cloud.google.com/run/detail/us-central1/"
          f"intake-agent/metrics?project=agent-era")
    print(f"     vertex https://console.cloud.google.com/apis/api/"
          f"aiplatform.googleapis.com/metrics?project=agent-era")
    print(f"     store  https://console.cloud.google.com/firestore/databases/"
          f"intake/data/panel/sessions/{sid}?project=agent-era")

    raw = max(OUT.glob("*.webm"), key=lambda f: f.stat().st_mtime)

    if CONSOLE.exists():
        # Overlay, not insert. Inserting would push everything after it later
        # and every narration line placed against this timeline would land on
        # the wrong frames. Overlaying keeps the clock identical, and the
        # placeholder was held for exactly this long.
        print("5. overlaying the console footage")
        start, end = marks["console"] - 1.0, marks["console_end"]
        overlaid = OUT / "with-console.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(CONSOLE),
            "-filter_complex",
            (f"[1:v]scale=1440:-2,setpts=PTS-STARTPTS+{start}/TB[c];"
             f"[0:v][c]overlay=x=(W-w)/2:y=(H-h)/2:"
             f"enable='between(t,{start},{end})'[v]"),
            "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", str(overlaid)], check=True)
        raw.unlink(missing_ok=True)
        raw = overlaid
    else:
        print("5. no console footage at demo/console-proof.mp4 — using the slate")

    print("6. muxing")
    subprocess.run(tl.mix_args(raw, FINAL), check=True)
    raw.unlink(missing_ok=True)
    print(f"   {FINAL}")


if __name__ == "__main__":
    asyncio.run(main())
