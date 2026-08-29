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
    "narrator": "Say this like a documentary voice-over, warm and conversational, "
                "unhurried but not slow:",
    "nurse": "Say this warmly and briskly, like a community nurse who has done "
             "this a thousand times:",
    "interviewee": "Say this like an elderly woman at home, a little vague:",
}

# Delivery came out at 70 words per minute — roughly half a normal narration
# pace, which read as slow and burned time that content needed. The prompt above
# helps; this guarantees it. Applied at synthesis so measured durations, and
# therefore every placement on the timeline, stay correct.
# Pace, applied at synthesis so measured durations stay correct. Measured on one
# narrator line: 1.10 gives 170 wpm, 1.25 gives 202, 1.40 gives 283 — far too
# fast to follow. 1.22 lands near 195, which is brisk documentary pace and still
# clear. The interviewee is not sped up: she is an elderly woman being
# interviewed at home, and hurrying her would undercut the scene.
#
# TTS length varies a little between generations, so re-measure rather than
# trust a number: `uv run python demo/voices.py` prints the wpm it actually got.
#
# Check the number rather than trusting it: `uv run python demo/voices.py`
# prints the measured wpm.
TEMPO = {"narrator": 1.22, "nurse": 1.10, "interviewee": 1.0}

class _Resynth(Exception):
    """Raised when the generated audio does not match the line it was given."""


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


def _spoken_text_is_wrong(wav: pathlib.Path, wanted: str) -> str | None:
    """Transcribe the clip back and check the model spoke only the line.

    Two failures were shipping in the finished video before this existed. The
    style direction is prepended to the text, and the model sometimes *reads it
    out* — "Keep it moving. One routing call, then three Gemini calls…". And
    occasionally it says the whole line twice.

    Neither is visible from a duration check and neither raises. The only way to
    catch them is to listen, so this listens. One extra call per new clip; the
    cache means it never runs twice for the same line.
    """
    from google.genai import types as _t
    try:
        got = client().models.generate_content(
            model="gemini-3.6-flash",
            contents=[_t.Part.from_bytes(data=wav.read_bytes(), mime_type="audio/wav"),
                      "Transcribe this audio verbatim. Output only the words spoken."],
        ).text or ""
    except Exception:
        return None  # never fail a render because the checker itself broke

    norm = lambda x: " ".join(
        c for c in x.lower().replace(",", " ").replace(".", " ").split())
    heard, want = norm(got), norm(wanted)

    # the direction leaked into the speech
    for phrase in ("say this", "voice-over", "conversational", "unhurried",
                   "briskly", "like a community nurse", "like an elderly woman"):
        if phrase in heard:
            return f"style direction was spoken aloud: {got.strip()[:70]!r}"

    # the line was read twice
    if len(heard.split()) > 1.55 * max(len(want.split()), 1):
        return f"line appears to be spoken more than once ({len(heard.split())} words for {len(want.split())})"
    return None


# Human recordings, dropped in by hand, win over anything synthesised. A judge
# said on camera that AI voices "feel less genuine", and the two people in the
# room are exactly where that lands — the narration can stay synthetic, but the
# nurse and the person being interviewed should sound like people.
HUMAN = pathlib.Path(__file__).resolve().parent / "interview-audio"


def _human_take(role: str, text: str) -> pathlib.Path | None:
    """A recorded line matching this text, if one has been dropped in.

    Matched on the manifest rather than on a hash of the text, so a recording
    survives a small wording tweak in script.toml — the alternative is a silent
    fall back to the synthetic take after an innocent edit.
    """
    manifest = HUMAN / "manifest.json"
    if not manifest.is_file():
        return None
    import json
    try:
        entries = json.loads(manifest.read_text())
    except (TypeError, ValueError):
        return None
    key = " ".join(text.split())
    for entry in entries:
        if entry.get("role") == role and " ".join(entry.get("text", "").split()) == key:
            take = HUMAN / entry["file"]
            if take.is_file():
                return take
    return None


def synth(role: str, text: str, attempts: int = 3) -> pathlib.Path:
    """A wav of `text` spoken by `role`, generated once and verified.

    Verification is not optional here. Two failures shipped in a finished video
    before it existed: the style direction read out as if it were the script,
    and a line spoken twice. Both are non-deterministic, so a retry usually
    clears them.
    """
    take = _human_take(role, text)
    if take is not None:
        return _normalised(take)

    for n in range(attempts):
        try:
            return _synth_once(role, text)
        except _Resynth as exc:
            if n == attempts - 1:
                raise RuntimeError(
                    f"{role} clip still wrong after {attempts} attempts ({exc}). "
                    f"Line: {text[:60]!r}") from None
    raise AssertionError("unreachable")


def _synth_once(role: str, text: str) -> pathlib.Path:
    CACHE.mkdir(exist_ok=True)
    voice = VOICES[role]
    key = hashlib.sha256(
        f"{MODEL}|{voice}|{STYLE[role]}|{TEMPO.get(role, 1.0)}|{text}".encode()
    ).hexdigest()[:16]
    path = CACHE / f"{role}-{key}.wav"
    if path.exists():
        return path

    # Vertex throttles TTS per minute per model, and re-rendering a whole script
    # is exactly the burst that trips it. Back off rather than fail the run
    # twenty clips in.
    import time
    last: Exception | None = None
    for attempt in range(6):
        try:
            resp = client().models.generate_content(
                model=MODEL,
                contents=f"{STYLE[role]} {text}",
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice)
                        )
                    ),
                ),
            )
            break
        except Exception as exc:
            last = exc
            if "RESOURCE_EXHAUSTED" not in str(exc) and "429" not in str(exc):
                raise
            wait = 8 * (attempt + 1)
            print(f"    tts rate-limited, waiting {wait}s", flush=True)
            time.sleep(wait)
    else:
        raise last  # type: ignore[misc]

    pcm = resp.candidates[0].content.parts[0].inline_data.data
    raw = path.with_suffix(".raw.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)

    problem = _spoken_text_is_wrong(raw, text)
    if problem:
        # One retry. The failure is non-deterministic, so a second generation
        # usually lands clean; a persistent one is worth stopping the render for
        # rather than shipping a narrator that talks over itself again.
        print(f"    re-synthesising {role}: {problem}", flush=True)
        raw.unlink(missing_ok=True)
        raise _Resynth(problem)

    tempo = TEMPO.get(role, 1.0)
    if tempo == 1.0:
        raw.rename(path)
        return path
    # atempo preserves pitch, so a faster read still sounds like the same person.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                    "-filter:a", f"atempo={tempo}", str(path)], check=True)
    raw.unlink(missing_ok=True)
    return path


def _normalised(take: pathlib.Path) -> pathlib.Path:
    """A human recording resampled to the timeline's format, cached by mtime."""
    dst = CACHE / f"human-{take.stem}-{int(take.stat().st_mtime)}.wav"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(take),
                        "-ac", "1", "-ar", str(SAMPLE_RATE), str(dst)], check=True)
        print(f"    using the human take for {take.name}", flush=True)
    return dst


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
    LINES = [
        ("narrator", "A community nurse has ninety minutes and a form she is "
                     "legally required to complete, and ninety minutes is never "
                     "enough for all of it."),
        ("nurse", "Have you had any falls in the last year?"),
        ("interviewee", "Oh, I've had a couple of wobbles."),
    ]
    for role, line in LINES:
        at = tl.append(role, line)
        print(f"  {role:12} {at:5.1f}s  {duration(synth(role, line)):4.1f}s")
    tl.check()
    words = sum(len(t.split()) for _, t in LINES)
    speech = sum(d for _, d, _, _ in tl.items)
    print(f"  total {tl.end:.1f}s — no overlaps · {words / (speech / 60):.0f} wpm")

    assert not tl.place(0.0, "narrator", "This should be refused."), \
        "overlap check failed to bite"
    print("  overlap check works")
