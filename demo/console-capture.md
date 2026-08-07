# Recording the Google Cloud proof

The rubric asks: *"Is there **visual proof of Google Cloud deployment** in the
video?"* and counts *"terminal logs, **database updates**, or UI changes"* as
proof of action.

I cannot log into your console, so this is the one segment you capture.

**Screenshots are enough — you do not need to screen-record.** Four stills, held
about five seconds each with a slow push-in and narration over the top, is
twenty seconds of proof and reads as deliberate rather than static. A screen
recording works too if you prefer; both go through the same tool.

```bash
# screenshots — the easy path
uv run python demo/splice.py ~/Desktop/run.png ~/Desktop/logs.png ~/Desktop/vertex.png

# or a recording
uv run python demo/splice.py ~/Desktop/console.mov --keep 20
```

It goes in at **2:05**, immediately after the second falls verdict — the moment
the narration is describing what the backend just did, so the console is
answering a question the viewer already has.

---

## Before you hit record

- Sign in to the **`agent-era`** project. Check the project picker says so on
  camera — that is half the proof.
- Close other tabs. Hide bookmarks (`⌘⇧B`). Full screen.
- **Zoom the browser to 125–150%.** Console text is small; at 100% it is
  unreadable once the video is compressed.
- Record at 1440×900 or larger, so it matches the rest of the cut.
- No narration needed — I lay the voice-over over it.

## Filming the logs live (the strongest shot)

Stills are valid proof — logs are timestamped records of real execution either
way. But watching lines arrive is more convincing, and it costs about ten cents.

1. Open the logs page, click **Stream logs**, zoom to **150%**, start recording.
2. Say go. I run:

   ```bash
   uv run python demo/generate-traffic.py
   ```

   It counts down eight seconds, then drives four real interview chunks through
   the deployed service — each routing to different items, so the lines say
   something different each time rather than repeating.
3. Watch `chunk routed to 2 of 14 open items: ['M14', 'M06']` appear as it
   happens. Record 30–45 seconds.
4. It prints the session id when it finishes, so the lines you filmed are
   traceable to one interview, and prints links to the Vertex and Firestore
   pages to grab while they are fresh.

The rest of the shots below can be stills.

## The three shots

One screenshot each. Take them at full-screen browser, and check the text is
legible before you send them — that is the only thing that can spoil this.

### Shot 1 · Cloud Run service

<https://console.cloud.google.com/run/detail/us-central1/intake-agent/metrics?project=agent-era>

- The **service name, region, and URL** must be legible in the frame.
- Show the **green tick** and "Serving 100% of traffic".
- Scroll gently to the **request-count chart** so the traffic spike from the
  demo run is visible.

### Shot 2 · Cloud Run logs

<https://console.cloud.google.com/run/detail/us-central1/intake-agent/observability/logs?project=agent-era>

- The most valuable frame in the whole segment.
- If you can, filter to `chunk routed` — those lines are the ADK pipeline
  reporting which items each chunk was routed to, which is the architecture
  claim proving itself in production:

  ```
  chunk routed to 2 of 14 open items: ['M14', 'M06']
  ```

- Do **not** filter to errors. Do not go hunting for the spend-cap 403s.

### Shot 3 · Vertex AI

Either of these; the dashboard is the stronger shot if it has data:

- <https://console.cloud.google.com/vertex-ai/generative/language/dashboard?project=agent-era>
- <https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/metrics?project=agent-era>

- Show **traffic against `aiplatform.googleapis.com`** — the request-count graph
  is what a judge wants: calls actually happening, in this project, recently.
- If a model name is visible, hold on it.

### Optional shot 4 · Firestore

<https://console.cloud.google.com/firestore/databases/intake/data/panel/sessions?project=agent-era>

- Open one document under `sessions` and expand `slots`. Seeing `M14` with
  `state: answered` and its quote is the "database updates" the rubric names.
- Skip if you are short on time; the video already shows Firestore in the app.

---

## Do not film

- The access code, any secret, or the `X-Intake-Key` value.
- Billing pages, your spend cap, or the 403s from when it fired.
- Other projects in the picker, especially anything work-related.
- Your email address in the top-right, if you would rather not publish it.

## Format

`.png` from `⌘⇧4` then space (window capture) is ideal — it keeps the window
chrome, which makes it obviously a real console rather than a crop. `.jpg` is
fine. For a recording, anything QuickTime or OBS produces works.

`splice.py` handles the rest: it scales to match the cut, letterboxes rather
than stretching, mutes any audio, and labels each frame "Deployed on Google
Cloud · project agent-era".
