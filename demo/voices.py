#!/usr/bin/env python3
"""Speech for the demo, via Gemini TTS on Vertex.

Three voices, deliberately distinct so a viewer can tell instantly who is
speaking without a caption:

    narrator     Charon    the voice-over
    nurse        Kore      the practitioner asking the questions
    interviewee  Sulafat   the person being interviewed

Two properties this module exists to guarantee, because the first attempt at
this video failed on both:

1. **Every clip's real duration is measured**, not assumed. The timeline is
   built from measured lengths, so lines cannot overlap.
2. **Clips are cached on disk by content hash.** Re-running the capture does
   not re-synthesise, so the audio is identical between takes and the timings
   stay stable.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess
import wave

from google import genai
from google.genai import types

CACHE = pathlib.Path(__file__).resolve().parent / "voice-cache"
MODEL = "gemini-2.5-flash-tts"
SAMPLE_RATE = 24000

VOICES = {
    "narrator": "Charon",
    "nurse": "Kore",
    "interviewee": "Sulafat",
}

# Delivery notes. Gemini TTS follows a natural-language style instruction, which
# is the difference between a demo that sounds like a screen reader and one that
# sounds like a room with two people in it.
STYLE = {
    "narrator": "Read this clearly and calmly, like a documentary voice-over. Measured pace:",
    "nurse": "Say this warmly and professionally, like a community nurse talking to a patient she likes:",
    "interviewee": "Say this like an elderly woman at home, a little vague and hesitant, unhurried:",
}

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        import os
        _client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "agent-era"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
    return _client


def synth(role: str, text: str) -> pathlib.Path:
    """Return a wav of `text` spoken by `role`, generating it only once."""
    CACHE.mkdir(exist_ok=True)
    voice = VOICES[role]
    key = hashlib.sha256(f"{MODEL}|{voice}|{STYLE[role]}|{text}".encode()).hexdigest()[:16]
    path = CACHE / f"{role}-{key}.wav"
    if path.exists():
        return path

    resp = client().models.generate_content(
        model=MODEL,
        contents=f"{STYLE[role]} {text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return path


def duration(path: pathlib.Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


class Timeline:
    """Speech clips placed on a timeline that is checked for overlap.

    `append` puts a clip after everything already placed. `place` puts one at an
    absolute time and refuses if it would collide — which is exactly the bug
    that made the first video unlistenable.
    """

    GAP = 0.35  # breath between consecutive lines

    def __init__(self) -> None:
        self.items: list[tuple[float, float, str, pathlib.Path]] = []

    @property
    def end(self) -> float:
        return max((t + d for t, d, _, _ in self.items), default=0.0)

    def append(self, role: str, text: str, gap: float | None = None) -> float:
        path = synth(role, text)
        at = self.end + (self.GAP if gap is None else gap)
        self.items.append((at, duration(path), role, path))
        return at

    def place(self, at: float, role: str, text: str) -> bool:
        """Place at an absolute time. False if it would overlap or run past."""
        path = synth(role, text)
        d = duration(path)
        for t0, d0, _, _ in self.items:
            if at < t0 + d0 + self.GAP and t0 < at + d + self.GAP:
                return False
        self.items.append((at, d, role, path))
        return True

    def fits(self, role: str, text: str, window: float) -> bool:
        return duration(synth(role, text)) <= window

    def check(self) -> None:
        """Fail loudly rather than ship overlapping speech."""
        ordered = sorted(self.items)
        for (t0, d0, r0, p0), (t1, _, r1, _) in zip(ordered, ordered[1:]):
            if t1 < t0 + d0:
                raise AssertionError(
                    f"speech overlap: {r0} at {t0:.1f}s (+{d0:.1f}s) "
                    f"collides with {r1} at {t1:.1f}s — {p0.name}")

    def mix_args(self, video: pathlib.Path, out: pathlib.Path) -> list[str]:
        """ffmpeg argv that lays every clip at its time and muxes onto `video`."""
        self.check()
        ordered = sorted(self.items)
        inputs = ["-i", str(video)]
        filters, labels = [], []
        for n, (at, _, _, path) in enumerate(ordered):
            inputs += ["-i", str(path)]
            ms = int(at * 1000)
            # No apad: padding twenty streams to infinity and mixing them is
            # what made ffmpeg fall over. adelay alone is enough — amix handles
            # inputs of different lengths.
            filters.append(f"[{n + 1}:a]adelay={ms}|{ms}[a{n}]")
            labels.append(f"[a{n}]")
        # normalize=0 keeps each voice at full level; without it ffmpeg divides
        # by the input count and everything becomes a whisper.
        filters.append(f"{''.join(labels)}amix=inputs={len(ordered)}:"
                       f"normalize=0:dropout_transition=0[aout]")
        return ["ffmpeg", "-y", "-loglevel", "error", *inputs,
                "-filter_complex", ";".join(filters),
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                "-shortest", str(out)]


if __name__ == "__main__":
    # Smoke test: one line per voice, and prove the overlap check bites.
    tl = Timeline()
    for role, line in [
        ("narrator", "A community nurse has ninety minutes and a form she must complete."),
        ("nurse", "Have you had any falls in the last year?"),
        ("interviewee", "Oh, I've had a couple of wobbles."),
    ]:
        at = tl.append(role, line)
        print(f"  {role:12} {at:5.1f}s  {duration(synth(role, line)):4.1f}s")
    tl.check()
    print(f"  total {tl.end:.1f}s — no overlaps")

    assert not tl.place(0.0, "narrator", "This should be refused."), \
        "overlap check failed to bite"
    print("  overlap check works")
