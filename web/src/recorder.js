/**
 * Microphone capture, chunked.
 *
 * MediaRecorder with a timeslice gives us a callback every N seconds without
 * any streaming machinery — ADR-0002 on purpose. Each blob is posted on its
 * own; there is no socket to drop and no session to resume.
 */
export const CHUNK_MS = 18000

export async function startRecording(onChunk) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
    .find((t) => MediaRecorder.isTypeSupported(t)) || ''

  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

  recorder.ondataavailable = async (event) => {
    if (!event.data || event.data.size === 0) return
    onChunk({
      audio_b64: await toBase64(event.data),
      mime_type: (mimeType || 'audio/webm').split(';')[0],
    })
  }

  recorder.start(CHUNK_MS)
  return {
    stop() {
      recorder.stop()
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
