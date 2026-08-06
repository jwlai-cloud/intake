#!/usr/bin/env bash
# Regenerate the synthetic audio fixtures. macOS `say` + ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

say -v Daniel -o "$tmp/q1.aiff" "Have you had any falls in the last year?"
say -v Fiona  -o "$tmp/a1.aiff" "Oh, I have had a couple of wobbles."
say -v Daniel -o "$tmp/q2.aiff" "How many times, and what happened the last time?"
say -v Fiona  -o "$tmp/a2.aiff" "Three times since Christmas. The last one was in May, I slipped coming down the stairs."

# One self-contained file per chunk — which is exactly what the fixed recorder
# emits, and the whole point: a timesliced MediaRecorder would make chunk 2 a
# headerless fragment that nothing can decode.
ffmpeg -y -loglevel error -i "$tmp/q1.aiff" -i "$tmp/a1.aiff" \
  -filter_complex "[0][1]concat=n=2:v=0:a=1[a]" -map "[a]" -c:a libopus -b:a 32k demo-chunk-1.webm
ffmpeg -y -loglevel error -i "$tmp/q2.aiff" -i "$tmp/a2.aiff" \
  -filter_complex "[0][1]concat=n=2:v=0:a=1[a]" -map "[a]" -c:a libopus -b:a 32k demo-chunk-2.webm
echo "wrote demo-chunk-1.webm demo-chunk-2.webm"
