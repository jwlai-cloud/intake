# Recording the Google Cloud proof

The rubric asks: *"Is there **visual proof of Google Cloud deployment** in the
video?"* and counts *"terminal logs, **database updates**, or UI changes"* as
proof of action.

I cannot log into your console, so this is the one segment you record. Aim for
**35–45 seconds of raw footage**; I will cut it to the ~20 seconds that fit.

Hand me the file and I will splice it in:

```bash
uv run python demo/splice.py path/to/your-console-recording.mov
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

## The three shots

Do them in one continuous take if you can; it is easier to trim than to join.

### Shot 1 · Cloud Run service — about 12s

<https://console.cloud.google.com/run/detail/us-central1/intake-agent/metrics?project=agent-era>

- Let the **service name, region, and URL** be readable for 3 seconds.
- Show the **green tick** and "Serving 100% of traffic".
- Scroll gently to the **request-count chart** so the traffic spike from the
  demo run is visible.

### Shot 2 · Cloud Run logs — about 15s

<https://console.cloud.google.com/run/detail/us-central1/intake-agent/logs?project=agent-era>

- The most valuable frames in the whole segment. Let real log lines sit still
  and readable.
- If you can, filter to `chunk routed` — those lines are the ADK pipeline
  reporting which items each chunk was routed to, which is the architecture
  claim proving itself in production:

  ```
  chunk routed to 2 of 14 open items: ['M14', 'M06']
  ```

- Do **not** filter to errors. Do not go hunting for the spend-cap 403s.

### Shot 3 · Vertex AI — about 12s

Either of these; the dashboard is the stronger shot if it has data:

- <https://console.cloud.google.com/vertex-ai/generative/language/dashboard?project=agent-era>
- <https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/metrics?project=agent-era>

- Show **traffic against `aiplatform.googleapis.com`** — the request-count graph
  is what a judge wants: calls actually happening, in this project, recently.
- If a model name is visible, hold on it.

### Optional shot 4 · Firestore — about 8s

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

Anything QuickTime or OBS produces is fine — `.mov` or `.mp4`, any frame rate.
`splice.py` normalises resolution and frame rate to match the cut. If the
recording has system audio on it, that is fine too; it gets muted, since the
narration plays over the top.
