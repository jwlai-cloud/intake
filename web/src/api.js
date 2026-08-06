const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/**
 * The access code is typed in by the user and kept in sessionStorage — never
 * baked into the build.
 *
 * Vite inlines `import.meta.env.*` at build time, so a `VITE_API_KEY` would
 * ship inside the JS bundle and be readable by anyone who opens it. Since the
 * endpoint spends money on Vertex AI per request, that is a published key to a
 * paid API. Typing it costs a reviewer five seconds and keeps the secret out of
 * every artifact we hand out.
 *
 * This is a stopgap for the contest, not an auth system. Firebase Auth ID
 * tokens replace it — see ADR-0012.
 */
const KEY_STORAGE = 'intake.accessCode'

export const getAccessCode = () => sessionStorage.getItem(KEY_STORAGE) || ''
export const setAccessCode = (code) => sessionStorage.setItem(KEY_STORAGE, code.trim())
export const clearAccessCode = () => sessionStorage.removeItem(KEY_STORAGE)

async function call(path, { method = 'GET', body } = {}) {
  const key = getAccessCode()
  const res = await fetch(BASE + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { 'X-Intake-Key': key } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const payload = await res.json().catch(() => ({}))
  if (!res.ok) throw Object.assign(new Error(payload.detail?.error || res.statusText), {
    status: res.status,
    detail: payload.detail,
  })
  return payload
}

export const listTemplates = () => call('/templates')
export const createSession = (templateId, practitionerId) =>
  call('/sessions', { method: 'POST', body: { template_id: templateId, practitioner_id: practitionerId } })
export const readSession = (id) => call(`/sessions/${id}`)
export const resolveItem = (id, body) => call(`/sessions/${id}/resolve`, { method: 'POST', body })
export const setHighlight = (id, hid, status) =>
  call(`/sessions/${id}/highlights/${hid}`, { method: 'POST', body: { status } })
export const generateReport = (id) => call(`/sessions/${id}/report`, { method: 'POST' })
export const postChunk = (id, body) => call(`/sessions/${id}/chunks`, { method: 'POST', body })

/**
 * Chunks that fail to POST are queued and replayed in order on the next
 * success. The server claims each `seq` once, so a replay is a no-op rather
 * than a double-counted answer — that contract is what makes this safe.
 */
export class ChunkQueue {
  constructor(sessionId, onState, onQueueChange = () => {}) {
    this.sessionId = sessionId
    this.onState = onState
    this.onQueueChange = onQueueChange
    this.pending = []
    this.seq = 0
    this.sending = false
  }

  enqueue(chunk) {
    this.pending.push({ seq: this.seq++, ...chunk })
    this.onQueueChange(this.pending.length)
    this.flush()
  }

  async flush() {
    if (this.sending) return
    this.sending = true
    while (this.pending.length) {
      const chunk = this.pending[0]
      try {
        const state = await postChunk(this.sessionId, chunk)
        this.pending.shift()
        this.onQueueChange(this.pending.length)
        this.onState(state)
      } catch {
        break // keep it queued; the next chunk or a reconnect retries in order
      }
    }
    this.sending = false
  }
}
