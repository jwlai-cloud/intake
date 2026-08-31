#!/usr/bin/env bash
# Record the six interview lines in your own voice, one at a time.
#
#   ./demo/record-interview.sh          # MacBook mic (device 1)
#   ./demo/record-interview.sh 0        # iPhone mic — usually much better
#
# Each take is saved straight into demo/interview-audio/ with the name the
# renderer expects, so there is nothing to rename or export. Re-run it any time;
# it asks before overwriting a take you already have.
#
# macOS will ask Terminal for microphone permission the first time. If you get
# silence, that prompt was probably declined:
#   System Settings > Privacy & Security > Microphone > enable your terminal.
set -uo pipefail

DEV="${1:-1}"
DIR="$(cd "$(dirname "$0")" && pwd)/interview-audio"
cd "$DIR" || exit 1

say_line() {  # file | who | target seconds | text
  local file="$1" who="$2" target="$3" text="$4"
  echo
  echo "──────────────────────────────────────────────────────────────"
  echo "  $who   (aim for about ${target}s — it does not need to be exact)"
  echo
  echo "  \"$text\""
  echo
  if [ -f "$file" ] && [ ! -f "$file.synthetic" ]; then
    read -r -p "  You already recorded this. Redo it? [y/N] " a
    [[ "$a" =~ ^[Yy]$ ]] || return
  fi
  # AVFoundation needs about half a second to open the device, and anything
  # said in that window is simply not captured — which silently ate the first
  # words of two takes. Start the recorder, let it settle, *then* cue.
  read -r -p "  Press Enter, wait for GO, then speak. Ctrl-C when done. "
  ffmpeg -hide_banner -loglevel error -f avfoundation -i ":$DEV" \
         -ac 1 -ar 24000 -y "$file" 2>/dev/null &
  local pid=$!
  sleep 1.2
  echo "  ▶ GO — speak now."
  wait $pid 2>/dev/null
  if [ -s "$file" ]; then
    local d
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$file" 2>/dev/null)
    printf "  saved %s (%.1fs against a %ss target)\n" "$file" "${d:-0}" "$target"
  else
    echo "  nothing recorded — check microphone permission for your terminal"
  fi
}

echo "Recording with audio device $DEV."
echo "Natural beats polished. The person is at home being asked about her health;"
echo "the vagueness in the first line is the whole point of the demo."

say_line 01-turn1-nurse.wav  "NURSE " 2.2 "Have you had any falls in the last year?"
say_line 02-turn1-person.wav "PERSON" 4.7 "Oh. I've had a couple of wobbles."
say_line 03-turn2-nurse.wav  "NURSE " 3.0 "How many times, and what happened the last one?"
say_line 04-turn2-person.wav "PERSON" 10.5 "Three times since Christmas. The last one was in May. I slipped coming down the stairs."
say_line 05-turn3-nurse.wav  "NURSE " 2.4 "And can I ask how much you drink in a week?"
say_line 06-turn3-person.wav "PERSON" 8.5 "That's my own business, thank you. Put down that I'd rather not say."

echo
echo "──────────────────────────────────────────────────────────────"
echo "Done. Tell Claude and the next render uses these instead of the synthetic takes."
