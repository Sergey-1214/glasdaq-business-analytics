import { Maximize2, Minimize2, X } from 'lucide-react'
import { useDashboardStore } from '../../store/dashboardStore'
import './Block.css'

export default function Block({ id, title, children, className = '' }) {
  const { focusedBlockId, setFocus, clearFocus, toggleBlock } = useDashboardStore()
  const isFocused = focusedBlockId === id

  return (
    <div className={`block ${className}`}>
      <div className="block__header">
        <span className="block__title">{title}</span>
        <div className="block__actions">
          <button
            className="block__btn"
            onClick={() => (isFocused ? clearFocus() : setFocus(id))}
            title={isFocused ? 'Свернуть' : 'Развернуть'}
          >
            {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
          {id !== 'map' && (
            <button
              className="block__btn"
              onClick={() => {
                if (isFocused) clearFocus()
                toggleBlock(id)
              }}
              title="Закрыть"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="block__body">{children}</div>
    </div>
  )
}
