// Rehearsal overlay: a visible cursor, click ripples, a caption bar and a clock.
//
// Playwright drives a real browser but records no pointer and no audio, so a
// raw capture shows state changing with no visible cause — you cannot tell what
// was clicked or when. This injects the missing feedback so the recording works
// as a choreography reference: watch it, then copy it live.
//
// Injected via addInitScript, so it survives navigation and runs before the app.

(() => {
  if (window.__intakeRehearsalOverlay) return
  window.__intakeRehearsalOverlay = true

  const css = `
    #rh-cursor {
      position: fixed; z-index: 2147483647; width: 22px; height: 22px;
      margin: -11px 0 0 -11px; border-radius: 50%; pointer-events: none;
      background: #ffffffcc; border: 2px solid #b25a00;
      box-shadow: 0 0 0 2px #b25a0055, 0 2px 6px #0004;
      transition: transform .08s ease-out;
    }
    .rh-ripple {
      position: fixed; z-index: 2147483646; width: 18px; height: 18px;
      margin: -9px 0 0 -9px; border-radius: 50%; pointer-events: none;
      border: 3px solid #b25a00; animation: rh-pop .55s ease-out forwards;
    }
    @keyframes rh-pop {
      from { transform: scale(.4); opacity: 1; }
      to   { transform: scale(3.4); opacity: 0; }
    }
    #rh-caption {
      position: fixed; left: 0; right: 0; bottom: 0; z-index: 2147483645;
      background: #123a43f2; color: #fffefa; pointer-events: none;
      font: 600 18px/1.35 Inter, ui-sans-serif, system-ui, sans-serif;
      letter-spacing: -.01em; padding: 14px 22px;
      display: flex; gap: 18px; align-items: baseline;
    }
    #rh-caption b { color: #7fdcbb; font-variant-numeric: tabular-nums;
                    font-weight: 800; min-width: 62px; }
    #rh-caption em { font-style: normal; opacity: .75; font-weight: 500; }
  `
  const style = document.createElement('style')
  style.textContent = css
  document.documentElement.appendChild(style)

  const cursor = document.createElement('div')
  cursor.id = 'rh-cursor'
  cursor.style.left = '-100px'
  const caption = document.createElement('div')
  caption.id = 'rh-caption'
  caption.innerHTML = '<b>0:00</b><span id="rh-text">Rehearsal</span>'

  const attach = () => {
    document.body.appendChild(cursor)
    document.body.appendChild(caption)
  }
  if (document.body) attach()
  else document.addEventListener('DOMContentLoaded', attach)

  addEventListener('mousemove', (e) => {
    cursor.style.left = e.clientX + 'px'
    cursor.style.top = e.clientY + 'px'
  }, true)

  addEventListener('mousedown', (e) => {
    cursor.style.transform = 'scale(.65)'
    const r = document.createElement('div')
    r.className = 'rh-ripple'
    r.style.left = e.clientX + 'px'
    r.style.top = e.clientY + 'px'
    document.body.appendChild(r)
    setTimeout(() => r.remove(), 600)
  }, true)

  addEventListener('mouseup', () => { cursor.style.transform = 'scale(1)' }, true)

  // Driven from the test: rhCaption('beat text', elapsedSeconds)
  window.rhCaption = (text, seconds) => {
    const mm = String(Math.floor(seconds / 60))
    const ss = String(Math.floor(seconds % 60)).padStart(2, '0')
    caption.querySelector('b').textContent = `${mm}:${ss}`
    caption.querySelector('#rh-text').innerHTML = text
  }
})()
