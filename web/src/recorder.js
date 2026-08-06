/**
 * Microphone capture, chunked into self-contained files.
 *
 * The obvious implementation is `recorder.start(CHUNK_MS)` and one POST per
 * `ondataavailable`. It does not work. With a timeslice, MediaRecorder emits a
 * *fragmented* stream: the first blob carries the container header (WebM's EBML
 * header, `1a45dfa3`) and every later blob is a raw continuation. Those later
 * blobs are not decodable on their own — `ffprobe` rejects one with "EBML
 * header parsing failed", and Gemini rejects it too. Sending them meant an
 * interview processed its first 18 seconds and silently discarded the rest.
 *
 * So each interval gets its own recorder: start, wait, stop, start again. The
 * `stop()` flushes one complete, independently decodable file. The cost is a
 * few milliseconds of audio lost at each boundary — inaudible at an 18-second
 * cadence, and an answer split across the seam is still caught, because
 * adjudication reads a rolling window of recent turns rather than one chunk.
 *
 * The alternative — cache the header blob and prepend it to every fragment —
 * has no gap but depends on container internals. Not worth it here.
 */
// 18s in normal use. Overridable because it is the single biggest lever on
// how a live demo feels: the first coverage update cannot arrive until one
// chunk has been captured *and* processed, and processing is ~20s regardless
// of chunk length. A shorter chunk brings the first tick forward without
// changing anything else.
//   VITE_CHUNK_MS=8000 npm run dev
export const CHUNK_MS = Number(import.meta.env.VITE_CHUNK_MS) || 18000

const PREFERRED = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']

export async function startRecording(onChunk) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = PREFERRED.find((t) => MediaRecorder.isTypeSupported(t)) || ''
  let stopped = false
  let timer = null
  let active = null

  const recordOne = () => {
    if (stopped) return
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    active = rec

    rec.ondataavailable = async (event) => {
      if (!event.data || event.data.size === 0) return
      onChunk({
        audio_b64: await toBase64(event.data),
        mime_type: (mimeType || 'audio/webm').split(';')[0],
      })
    }
    // Chain from onstop, not from a fixed interval: the next recording starts
    // only once this one has flushed, so two recorders never share the stream.
    rec.onstop = () => recordOne()

    rec.start()
    timer = setTimeout(() => {
      if (rec.state !== 'inactive') rec.stop()
    }, CHUNK_MS)
  }

  recordOne()

  return {
    stop() {
      stopped = true
      clearTimeout(timer)
      if (active && active.state !== 'inactive') {
        active.onstop = null   // do not chain a new recording after the last flush
        active.stop()          // still fires ondataavailable, so the tail is sent
      }
      stream.getTracks().forEach((t) => t.stop())
    },
  }
}

function toBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = reject
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.readAsDataURL(blob)
  })
}
