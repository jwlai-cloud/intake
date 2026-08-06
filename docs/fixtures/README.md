# Audio fixtures

Two synthetic interview chunks, generated with macOS `say` and `ffmpeg`. No real
voices, no real interview — the repo and the video are public.

    chunk 1  "Have you had any falls in the last year?"
             "Oh, I have had a couple of wobbles."          → M14 partial

    chunk 2  "How many times, and what happened the last time?"
             "Three times since Christmas. The last one was
              in May, I slipped coming down the stairs."     → M14 answered

They exist because the audio path is otherwise only testable by speaking into a
microphone, and it is the path that broke: chunks after the first were arriving
without a container header and failing silently. Replay them against a running
service to check the whole turn end to end:

```bash
python3 -c "
import base64, json, sys
p = sys.argv[1]
print(json.dumps({'seq': int(sys.argv[2]),
                  'audio_b64': base64.b64encode(open(p,'rb').read()).decode(),
                  'mime_type': 'audio/webm'}))" docs/fixtures/demo-chunk-1.webm 1 > /tmp/body.json

curl -s -X POST "$URL/sessions/$SID/chunks" \
  -H "X-Intake-Key: $KEY" -H 'Content-Type: application/json' \
  --data-binary @/tmp/body.json
```

Regenerate with `docs/fixtures/make.sh`.
