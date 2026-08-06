// Rehearsal overlay: a visible cursor, click ripples, a caption bar and a clock.
//
// Playwright drives a real browser but records no pointer and no audio, so a
// raw capture shows state changing with no visible cause — you cannot tell what
// was clicked, or when, or why it mattered.
//
// Two ordering rules, both learned the hard way. This runs as an init script,
// which fires *before the document exists*: the first version called
// `document.documentElement.appendChild` at top level, threw on a null
// documentElement, and took the whole file down with it. And because it set its
// "already installed" flag on the first line, the retry returned early forever.
// So: the public API is defined immediately, DOM work waits for a document, and
// the flag is only set once installation has actually succeeded.

(() => {
  if (window.__intakeOverlayReady) return

  const state = { cursor: null, caption: null }

  const CSS = `
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
    @keyframes rh-glow {
      from { box-shadow: 0 0 0 9999px #12303c33, 0 0 0 0 #b25a0000; }
      to   { box-shadow: 0 0 0 9999px #12303c33, 0 0 0 12px #b25a0033; }
    }
    #rh-caption {
      position: fixed; left: 0; right: 0; bottom: 0; z-index: 2147483645;
      background: linear-gradient(#123a4300, #123a43f7 26%);
      color: #fffefa; pointer-events: none;
      font: 700 27px/1.28 Inter, ui-sans-serif, system-ui, sans-serif;
      letter-spacing: -.02em; padding: 54px 44px 28px;
    }
    #rh-caption b {
      color: #7fdcbb; font-variant-numeric: tabular-nums; font-weight: 800;
      font-size: 19px; margin-right: 16px;
    }
    #rh-caption em {
      font-style: normal; display: block; margin-top: 8px;
      font-size: 20px; font-weight: 500; opacity: .85;
    }
  `

  function install() {
    if (state.caption || !document.body) return
    const style = document.createElement('style')
    style.textContent = CSS
    document.head.appendChild(style)

    state.cursor = document.createElement('div')
    state.cursor.id = 'rh-cursor'
    state.cursor.style.left = '-100px'

    state.caption = document.createElement('div')
    state.caption.id = 'rh-caption'
    state.caption.innerHTML = '<b>0:00</b><span id="rh-text"></span>'

    document.body.append(state.cursor, state.caption)
    window.__intakeOverlayReady = true
  }

  // Pointer feedback. Listeners are safe to attach before the body exists.
  addEventListener('mousemove', (e) => {
    if (!state.cursor) return
    state.cursor.style.left = e.clientX + 'px'
    state.cursor.style.top = e.clientY + 'px'
  }, true)

  addEventListener('mousedown', (e) => {
    if (!state.cursor || !document.body) return
    state.cursor.style.transform = 'scale(.65)'
    const r = document.createElement('div')
    r.className = 'rh-ripple'
    r.style.left = e.clientX + 'px'
    r.style.top = e.clientY + 'px'
    document.body.appendChild(r)
    setTimeout(() => r.remove(), 620)
  }, true)

  addEventListener('mouseup', () => {
    if (state.cursor) state.cursor.style.transform = 'scale(1)'
  }, true)

  // --- public API, defined before any DOM work can fail -------------------

  window.rhCaption = (html, seconds) => {
    install()
    if (!state.caption) return false
    const mm = Math.floor(seconds / 60)
    const ss = String(Math.floor(seconds % 60)).padStart(2, '0')
    state.caption.querySelector('b').textContent = `${mm}:${ss}`
    state.caption.querySelector('#rh-text').innerHTML = html
    return true
  }

  // Ring the row that just changed, so the eye goes to it. Without this a
  // viewer simply misses the one item that mattered.
  window.rhHighlight = (itemId) => {
    install()
    window.rhClearHighlight()
    const row = [...document.querySelectorAll('.item')].find(
      (el) => (el.querySelector('h3')?.textContent || '').startsWith(itemId))
    if (!row) return false
    row.scrollIntoView({ block: 'center', behavior: 'smooth' })
    setTimeout(() => {
      const r = row.getBoundingClientRect()
      const ring = document.createElement('div')
      ring.className = 'rh-ring'
      Object.assign(ring.style, {
        position: 'fixed', zIndex: '2147483644', pointerEvents: 'none',
        left: (r.left - 9) + 'px', top: (r.top - 9) + 'px',
        width: (r.width + 18) + 'px', height: (r.height + 18) + 'px',
        border: '3px solid #b25a00', borderRadius: '15px',
        animation: 'rh-glow 1.1s ease-in-out infinite alternate',
      })
      document.body.appendChild(ring)
    }, 420)
    return true
  }

  window.rhClearHighlight = () => {
    document.querySelectorAll('.rh-ring').forEach((n) => n.remove())
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install)
  } else {
    install()
  }
})()
