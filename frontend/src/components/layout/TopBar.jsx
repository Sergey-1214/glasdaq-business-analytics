import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, LogOut } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import NotificationPanel from '../ui/NotificationPanel'
import WorkspaceSelector from '../ui/WorkspaceSelector'
import './TopBar.css'

export default function TopBar() {
  const [selectorOpen, setSelectorOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const workspaceBtnRef = useRef(null)
  const bellBtnRef = useRef(null)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="topbar">
      <div className="topbar__logo">
        <img src="/glasdaq3.png" alt="Glasdaq" className="topbar__logo-img" />
      </div>

      <div className="topbar__center">
        <button
          ref={workspaceBtnRef}
          className="topbar__workspace-btn"
          onClick={() => setSelectorOpen((value) => !value)}
          aria-haspopup="dialog"
          aria-expanded={selectorOpen}
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
        {user && (
          <span className="topbar__username" title={user.email}>{user.username}</span>
        )}

        <div className="topbar__notif-wrapper">
          <button
            ref={bellBtnRef}
            className={`topbar__icon-btn ${notifOpen ? 'topbar__icon-btn--active' : ''}`}
            title="Уведомления"
            onClick={() => setNotifOpen((value) => !value)}
            aria-label="Уведомления"
            aria-haspopup="dialog"
            aria-expanded={notifOpen}
          >
            <Bell size={15} />
          </button>
          {notifOpen && (
            <NotificationPanel
              triggerRef={bellBtnRef}
              onClose={() => setNotifOpen(false)}
            />
          )}
        </div>

        <button className="topbar__icon-btn" title="Выйти" onClick={handleLogout} aria-label="Выйти">
          <LogOut size={15} />
        </button>
      </div>
    </header>
  )
}
