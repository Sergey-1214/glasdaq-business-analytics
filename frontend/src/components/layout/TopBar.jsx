import { useState, useRef } from 'react'
import WorkspaceSelector from '../ui/WorkspaceSelector'
import './TopBar.css'

export default function TopBar() {
  const [selectorOpen, setSelectorOpen] = useState(false)
  const workspaceBtnRef = useRef(null)

  return (
    <header className="topbar">
      <div className="topbar__logo">
        <img src="/glasdaq3.png" alt="Glasdaq" className="topbar__logo-img" />
      </div>

      <div className="topbar__center">
        <button
          ref={workspaceBtnRef}
          className="topbar__workspace-btn"
          onClick={() => setSelectorOpen((v) => !v)}
        >
          Рабочая область ▾
        </button>
        {selectorOpen && (
          <WorkspaceSelector
            triggerRef={workspaceBtnRef}
            onClose={() => setSelectorOpen(false)}
          />
        )}
      </div>

      <div className="topbar__right">
        <span className="topbar__balance">1337.69 RUB</span>
        <button className="topbar__icon-btn" title="Уведомления">🔔</button>
        <button className="topbar__icon-btn" title="Профиль">👤</button>
      </div>
    </header>
  )
}
