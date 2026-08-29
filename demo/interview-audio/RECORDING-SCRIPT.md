# Interview lines — for human recording

Only the two people in the room. The narration is separate and stays as it is.

Record each line as its own file and keep the file names below. Match the
target length within about a second — the video's timing is built from these
durations, so a wildly longer take pushes everything after it out of sync.

Natural is better than polished. The person should sound like someone at home
being asked about their health, including the hesitation — the whole point of
the falls line is that it is vague.

| File | Voice | Target | Line |
|---|---|---|---|
| `01-turn1-nurse.wav` | NURSE | 2.2s | Have you had any falls in the last year? |
| `02-turn1-person.wav` | PERSON | 4.7s | Oh. I've had a couple of wobbles. |
| `03-turn2-nurse.wav` | NURSE | 3.0s | How many times, and what happened the last one? |
| `04-turn2-person.wav` | PERSON | 10.5s | Three times since Christmas. The last one was in May. I slipped coming down the stairs. |
| `05-turn3-nurse.wav` | NURSE | 2.4s | And can I ask how much you drink in a week? |
| `06-turn3-person.wav` | PERSON | 8.5s | That's my own business, thank you. Put down that I'd rather not say. |

## When you have them

Drop the recorded wavs into `demo/interview-audio/` with the same names,
then the render swaps them in place of the synthetic ones.

Mono or stereo both fine, any sample rate — they get normalised on the way in.