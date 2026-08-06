# Demo pack

Everything needed to rehearse the video, and then to run it live with a real
person. The shot list is `../docs/demo-script.md`; this directory is the
machinery behind it.

| File | What it is |
|---|---|
| `rehearse.py` | Drives the deployed service through the exact beats and records a narrated mp4. Prints when each item actually changes state. |
| `overlay.js` | Injected into the page during a rehearsal: visible cursor, click ripples, caption bar, running clock. A raw Playwright capture has no pointer and no sound, so state appears to change with no visible cause. |
| `preroll-1.txt`, `preroll-2.txt` | Two paste-and-sends that take a fresh session to **11 of 14 resolved** in about 50 seconds. Not filmed — this is the state you start recording from. |
| `rehearsal/intake-rehearsal.mp4` | The reference recording. h264 + aac, plays anywhere. Gitignored — regenerate it. |

## Rehearse

```bash
# terminal 1 — the client, against the deployed service
cd web && VITE_API_BASE=https://intake-agent-320877670799.us-central1.run.app \
  VITE_CHUNK_MS=8000 npm run dev

# terminal 2
export INTAKE_KEY=<the access code>
uv run --with playwright python demo/rehearse.py
```

Watch `rehearsal/intake-rehearsal.mp4`. That is what the app does, in the order
it does it, with the pointer visible and each beat narrated — the choreography
to follow when a real person is answering instead of a script.

`--no-narrate` skips the voice track. Narration uses macOS `say`; the mp4
conversion uses ffmpeg. Both are skipped with a warning if absent, and you still
get the silent capture.

**Re-run it the morning of the take.** Model latency drifts, and the shot list
is built on these numbers.

## Run it for real

1. Start the client as above.
2. Paste `preroll-1.txt` into the typed box, send, wait ~28s.
3. Paste `preroll-2.txt`, send, wait ~21s. You should read **11 of 14**.
4. Check M14, M20 and M24 are still open. Start recording.
5. Follow `../docs/demo-script.md` from Act 1.

The pre-roll uses the typed box because it is setup, not performance. From the
moment you press record, everything is spoken and live.

## The three live beats, and why these words

Each phrasing has been run repeatedly against the deployed adjudicator and
produces the same verdict every time. **Do not improvise them** — an unedited
take cannot survive a wrong tick.

| Said | Item | Result | Measured |
|---|---|---|---|
| *"Oh, I've had a couple of wobbles."* | M14 | **Mentioned** — count and circumstances still missing | ~12s |
| *"Three times since Christmas. The last one was in May, I slipped coming down the stairs."* | M14 | **Answered**, and M15 opens | ~16s |
| *"That's my own business, thank you. Put down that I'd rather not say."* | M24 | **Declined** | ~15s |

Between them that is all three resolution states, live, plus a conditional item
appearing mid-interview. The gate then has two items left, and the agent drafts
their follow-ups itself.

## If you swap the words

Re-test before recording:

```bash
cd eval && uv run python run_eval.py --item M14
```

The interviewee does not have to say these sentences exactly in a real
interview — the adjudicator handles paraphrase, which is the whole point. But
on an unedited take, use the phrasings that have been measured.
