import { useEffect, useRef } from 'react'
import { BellOff } from 'lucide-react'
import './NotificationPanel.css'

export default function NotificationPanel({ onClose, triggerRef }) {
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (triggerRef?.current && triggerRef.current.contains(e.target)) return
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose, triggerRef])

  return (
    <div className="notif-panel" ref={ref}>
      <div className="notif-panel__header">
        <span className="notif-panel__title">Уведомления</span>
      </div>
      <div className="notif-panel__empty">
        <BellOff size={32} className="notif-panel__empty-icon" />
        <span>Нет уведомлений</span>
      </div>
    </div>
  )
}
