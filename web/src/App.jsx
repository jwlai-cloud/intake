import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from './api'
import { ChunkQueue, getAccessCode, setAccessCode } from './api'
import { startRecording } from './recorder'
import './app.css'

const Check = () => (
  <svg viewBox="0 0 24 24" fill="none" strokeWidth="3">
    <path d="m5 12 4 4L19 6" />
  </svg>
)

/** Slot state → the prototype's visual vocabulary. */
const CLASS_FOR = {
  open: 'open',
  partial: 'mentioned',
  answered: 'answered',
  declined: 'answered',
  escalated: 'answered',
}
const BADGE_FOR = {
  open: 'Open',
  partial: 'Mentioned',
  answered: 'Answered',
  declined: 'Declined',
  escalated: 'Escalated',
}

export default function App() {
  const [templates, setTemplates] = useState([])
  const [session, setSession] = useState(null)
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [queued, setQueued] = useState(0)
  const [gate, setGate] = useState(null)
  const [error, setError] = useState('')
  const queue = useRef(null)
  const recorder = useRef(null)

  useEffect(() => {
    api.listTemplates().then((r) => setTemplates(r.templates)).catch(() =>
      setError('Cannot reach the agent service. Is the backend running on :8000?'))
  }, [])

  useEffect(() => {
    if (!recording) return
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [recording])

  const begin = async (templateId) => {
    setError('')
    try {
      const s = await api.createSession(templateId, 'practitioner-demo')
      setSession(s)
      queue.current = new ChunkQueue(s.session_id, setSession, setQueued)
    } catch (err) {
      setError(err.status === 401
        ? 'That access code was not accepted. Check it and try again.'
        : err.message)
    }
  }

  const toggleRecording = async () => {
    if (recording) {
      recorder.current?.stop()
      recorder.current = null
      setRecording(false)
      return
    }
    try {
      recorder.current = await startRecording((chunk) => queue.current.enqueue(chunk))
      setRecording(true)
    } catch {
      setError('Microphone permission is required to record the interview.')
    }
  }

  // The typed path exists so a venue with unusable audio does not kill the demo,
  // and so the pipeline can be exercised without a microphone at all.
  const sendText = async (text) => {
    if (!text.trim()) return
    queue.current.enqueue({ text })
  }

  const finish = async () => {
    try {
      const s = await api.generateReport(session.session_id)
      setSession(s)
      setGate(null)
    } catch (err) {
      if (err.status === 409) setGate(err.detail.outstanding)
      else setError(err.message)
    }
  }

  const resolve = async (body) => {
    const s = await api.resolveItem(session.session_id, body)
    setSession(s)
    // When the last outstanding item is resolved, produce the report rather
    // than leaving an empty modal sitting over the page — the gate is a router,
    // and once it has nothing left to route it should get out of the way.
    if (s.gate_open) {
      setGate(null)
      try {
        setSession(await api.generateReport(s.session_id))
      } catch (err) {
        setError(err.message)
      }
      return
    }
    setGate((g) => g?.filter((o) => o.item_id !== body.item_id) ?? null)
  }

  if (!session) {
    return <Landing templates={templates} onBegin={begin} error={error} />
  }
  if (session.report) {
    return <Report session={session} />
  }

  return (
    <>
      <TopBar title={session.title} recording={recording} elapsed={elapsed} />
      <Live
        session={session}
        recording={recording}
        queued={queued}
        error={error}
        onToggleRecording={toggleRecording}
        onSendText={sendText}
        onFinish={finish}
        onHighlight={async (hid, status) =>
          setSession(await api.setHighlight(session.session_id, hid, status))}
      />
      {gate && <Gate outstanding={gate} session={session}
                     onResolve={resolve} onClose={() => setGate(null)} />}
    </>
  )
}

function TopBar({ title, recording, elapsed }) {
  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const ss = String(elapsed % 60).padStart(2, '0')
  return (
    <header className="top">
      <div className="brand">intake</div>
      <div className="tag">your second chair — nothing leaves the room unanswered.</div>
      <div className="spacer" />
      <div className="job">{title}</div>
      {recording && (
        <div className="recording"><i className="dot" />RECORDING</div>
      )}
      <div className="timer">{mm}:{ss}</div>
    </header>
  )
}

function Landing({ templates, onBegin, error }) {
  return (
    <>
      <header className="top">
        <div className="brand">intake</div>
        <div className="tag">your second chair — nothing leaves the room unanswered.</div>
      </header>
      <main>
        <section className="panel empty">
          <div className="empty-mark">○</div>
          <div className="eyebrow">Choose the form for this visit</div>
          <h2>Ready when the interview begins</h2>
          <p>
            Required items appear here as they are raised and <b>substantively
            answered</b>. No interviewee identity is asked for or indexed —
            answers are stored as the quotes they were spoken in, and go when
            the session does.
          </p>
          <AccessCodeField />
          {error && <p className="missing">{error}</p>}
          <div className="actions" style={{ justifyContent: 'center' }}>
            {templates.map((t) => (
              <button key={t.template_id} className="btn" onClick={() => onBegin(t.template_id)}>
                {t.title} · {t.required} items
              </button>
            ))}
          </div>
        </section>
      </main>
    </>
  )
}

/**
 * The access code is typed, not built in. See the note in api.js: a key inlined
 * by Vite ships inside the bundle, and this endpoint spends money per request.
 */
function AccessCodeField() {
  const [code, setCode] = useState(getAccessCode())
  const [saved, setSaved] = useState(Boolean(getAccessCode()))

  return (
    <div style={{ maxWidth: 440, margin: '0 auto 22px' }}>
      <label className="eyebrow" htmlFor="accessCode"
             style={{ display: 'block', marginBottom: 7 }}>
        Access code
      </label>
      <div className="actions">
        <input
          id="accessCode"
          type="password"
          value={code}
          onChange={(e) => { setCode(e.target.value); setSaved(false) }}
          onBlur={() => { setAccessCode(code); setSaved(Boolean(code.trim())) }}
          placeholder="Paste the code from the submission notes"
          style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8,
                   padding: '9px 11px' }}
        />
        <button className="mini confirm"
                onClick={() => { setAccessCode(code); setSaved(Boolean(code.trim())) }}>
          {saved ? 'Saved' : 'Save'}
        </button>
      </div>
      <p className="why" style={{ marginTop: 8 }}>
        Held in this tab only, never stored in the build. Every interview turn
        calls Vertex AI, so the endpoint is not left open.
      </p>
    </div>
  )
}

function Live({ session, recording, queued, error, onToggleRecording, onSendText,
                onFinish, onHighlight }) {
  const [draft, setDraft] = useState('')
  const { resolved, required } = session.coverage
  const pct = required ? Math.round((resolved / required) * 100) : 0
  const outstanding = session.outstanding.length

  return (
    <main>
      <div className="session-head">
        <div>
          <div className="eyebrow">{session.subtitle}</div>
          <h1>{session.title}</h1>
        </div>
        <div className="progress">
          <strong>{resolved} of {required} required items resolved</strong>
          <div className="track"><div className="fill" style={{ width: `${pct}%` }} /></div>
        </div>
      </div>

      <div className="grid">
        <section className="panel">
          <div className="panel-title">
            <h2>Required items</h2>
            <small>Check before leaving</small>
          </div>
          <div className="items">
            {session.items.map((item) => <ItemRow key={item.id} item={item} />)}
          </div>
        </section>

        <aside>
          <section className="panel next">
            <div className="eyebrow">Suggested next question</div>
            <div className="prompt">
              {session.next_question
                ? `“${session.next_question.prompt}”`
                : '“Start recording and the next question will appear here.”'}
            </div>
            <div className="why">
              {session.next_question?.why || 'Driven by whichever required item is closest to complete.'}
            </div>
            <div className="actions">
              <button className="btn" onClick={onToggleRecording}>
                {recording ? 'Stop recording' : 'Start recording'}
              </button>
            </div>
            <div className="why" style={{ marginTop: 14 }}>
              Or type what was said — useful when the room is too noisy to record.
            </div>
            <div className="actions">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { onSendText(draft); setDraft('') }
                }}
                placeholder="Interviewee: I've had a couple of wobbles…"
                style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, padding: '9px 11px' }}
              />
              <button className="mini confirm" onClick={() => { onSendText(draft); setDraft('') }}>
                Send
              </button>
            </div>
            {queued > 0 && (
              <div className="why" style={{ marginTop: 10 }}>
                {queued} chunk{queued > 1 ? 's' : ''} queued locally — they will replay in order.
              </div>
            )}
            {error && <div className="why missing">{error}</div>}
          </section>

          <section className="panel highlights">
            <div className="panel-title">
              <h2>Proposed highlights</h2>
              <small>Tap once to confirm</small>
            </div>
            {session.highlights.filter((h) => h.status === 'proposed').map((h) => (
              <div className="highlight" key={h.id}>
                <strong>{h.title}</strong>
                <p>“{h.quote}”</p>
                <div className="actions">
                  <button className="mini confirm" onClick={() => onHighlight(h.id, 'confirmed')}>
                    Confirm
                  </button>
                  <button className="mini" onClick={() => onHighlight(h.id, 'dismissed')}>
                    Dismiss
                  </button>
                </div>
              </div>
            ))}
            {!session.highlights.some((h) => h.status === 'proposed') && (
              <div className="highlight"><p>Nothing proposed yet.</p></div>
            )}
          </section>
        </aside>
      </div>

      <div className="finish">
        <span>
          {outstanding === 0
            ? 'Every required item has a recorded resolution.'
            : `${outstanding} item${outstanding > 1 ? 's' : ''} still need a recorded answer`}
        </span>
        <button className="btn ghost" onClick={onFinish}>Finish &amp; generate report</button>
      </div>
    </main>
  )
}

function ItemRow({ item }) {
  // State drives the colour, always. "Mentioned" is the state the product
  // exists to show, so a high-risk item must not lose it — high risk changes
  // what is *offered* (no suggested answer, ADR-0006), not what is true about
  // the record.
  const cls = CLASS_FOR[item.state] || 'open'
  const resolved = ['answered', 'declined', 'escalated'].includes(item.state)

  return (
    <article className={`item ${cls}`}>
      <div className="state">{item.state === 'answered' ? <Check /> : null}</div>
      <div>
        <h3>{item.id} · {item.prompt}</h3>
        {resolved ? (
          item.evidence
            ? <div className="quote">“{item.evidence}”</div>
            : <p>{item.reason || BADGE_FOR[item.state]}</p>
        ) : (
          <p className={cls === 'risk' ? 'risk-note' : cls === 'mentioned' ? 'missing' : ''}>
            {item.missing?.length
              ? `Still missing: ${item.missing.join('; ')}`
              : 'No recorded answer.'}
          </p>
        )}
        {/* High-risk items get the quote and nothing else — no suggested
            answer is ever offered for them (ADR-0006). */}
        {!resolved && item.evidence && (
          <div className="quote">Heard: “{item.evidence}”</div>
        )}
        {!resolved && item.high_risk && (
          <p className="risk-note">High risk — no suggested answer. Write this one yourself.</p>
        )}
      </div>
      <span className="status">{BADGE_FOR[item.state]}</span>
    </article>
  )
}

function Gate({ outstanding, session, onResolve, onClose }) {
  return (
    <div className="gate" role="dialog" aria-modal="true" aria-labelledby="gateTitle">
      <section className="gate-card">
        <div className="eyebrow">Before the report is generated</div>
        <h2 id="gateTitle">
          {outstanding.length} item{outstanding.length > 1 ? 's need' : ' needs'} a resolution
        </h2>
        <p>
          Choose how each item should be closed. Return to the interview, record
          that a response was declined, or have the follow-up action drafted and
          filed. Nothing is ever left silently blank.
        </p>
        {outstanding.map((o) => (
          <GateItem key={o.item_id} outstanding={o} onResolve={onResolve} onClose={onClose} />
        ))}
        <div className="gate-foot">
          <span>Each item needs one recorded resolution.</span>
          <button className="btn ghost" onClick={onClose}>Return to interview</button>
        </div>
      </section>
    </div>
  )
}

function GateItem({ outstanding, onResolve, onClose }) {
  const [mode, setMode] = useState(null)
  const [reason, setReason] = useState('')
  const [done, setDone] = useState('')

  if (done) return (
    <section className="gate-item">
      <h3>{outstanding.item_id}</h3>
      <div className="why">{done}</div>
    </section>
  )

  return (
    <section className="gate-item">
      <h3>{outstanding.item_id} · {outstanding.prompt}</h3>
      <p>
        {outstanding.missing?.length
          ? `Still missing: ${outstanding.missing.join('; ')}`
          : 'No recorded answer.'}
      </p>
      {mode === null && (
        <div className="resolution">
          <button onClick={onClose}>
            <b>Ask now</b>
            <small>Return to the interview with this item still open.</small>
          </button>
          <button
            disabled={!outstanding.accepts_declined}
            title={outstanding.accepts_declined ? '' : 'This item may not be declined'}
            onClick={() => setMode('declined')}>
            <b>Record as declined</b>
            <small>
              {outstanding.accepts_declined
                ? 'Record the reason the response was declined.'
                : 'Not permitted for this item by the form.'}
            </small>
          </button>
          <button onClick={async () => {
            setDone('Drafting the follow-up action…')
            await onResolve({ item_id: outstanding.item_id, resolution: 'escalated' })
            setDone('Follow-up action drafted and filed for this item.')
          }}>
            <b>Escalate</b>
            <small>The agent drafts and files a follow-up action.</small>
          </button>
        </div>
      )}
      {mode === 'declined' && (
        <div className="resolution">
          <div style={{ gridColumn: '1/-1' }}>
            <label className="eyebrow" style={{ display: 'block', marginBottom: 7 }}>
              Reason for declined response
            </label>
            <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                      placeholder="Record the reason"
                      style={{ width: '100%', border: '1px solid var(--line)',
                               borderRadius: 7, padding: 9, resize: 'vertical' }} />
            <div className="actions" style={{ marginTop: 8 }}>
              <button className="mini confirm" onClick={async () => {
                await onResolve({ item_id: outstanding.item_id, resolution: 'declined', reason })
                setDone('Declined resolution recorded with reason.')
              }}>Save declined resolution</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function Report({ session }) {
  const report = session.report
  return (
    <>
      <header className="top">
        <div className="brand">intake</div>
        <div className="tag">your second chair — nothing leaves the room unanswered.</div>
      </header>
      <main>
        <div className="report">
          <div className="report-head">
            <div>
              <div className="eyebrow">Generated report</div>
              <h1>{report.title}</h1>
              <div className="report-meta">
                {report.generated_from.resolved} of {report.generated_from.required} required
                items resolved or formally recorded
              </div>
            </div>
            <div className="report-actions">
              <button className="btn ghost" onClick={() => window.print()}>Export PDF</button>
              <button className="btn">Finalise report</button>
            </div>
          </div>

          {report.sections.map((section) => (
            <section className="panel report-section" key={section.id}>
              <h2>{section.title}</h2>
              {section.entries.map((entry) => (
                <div className="edit" contentEditable suppressContentEditableWarning key={entry.item_id}>
                  <b>{entry.item_id}</b> — {entry.text}
                </div>
              ))}
            </section>
          ))}

          {report.flags.length > 0 && (
            <section className="panel report-section">
              <h2>Flags</h2>
              {report.flags.map((f, i) => <div className="flagrow" key={i}>{f.note}</div>)}
            </section>
          )}

          {report.followups.length > 0 && (
            <section className="panel report-section">
              <h2>Follow-ups filed</h2>
              {report.followups.map((f, i) => (
                <div className="followrow" key={i}>
                  <b>{f.item_id}</b> — {f.outstanding} · {f.why} → <b>{f.destination}</b>
                </div>
              ))}
            </section>
          )}
        </div>
      </main>
    </>
  )
}
