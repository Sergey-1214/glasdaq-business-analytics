import { Maximize2, Minimize2, X } from 'lucide-react'
import { useDashboardStore } from '../../store/dashboardStore'
import ErrorBoundary from './ErrorBoundary'
import './Block.css'

export default function Block({ id, title, children, className = '', dragListeners }) {
  const { focusedBlockId, setFocus, clearFocus, toggleBlock } = useDashboardStore()
  const isFocused = focusedBlockId === id

  return (
    <div className={`block ${className}`}>
      <div className="block__header" {...dragListeners}>
        <span className="block__title">{title}</span>
        <div className="block__actions">
          <button
            className="block__btn"
            onClick={() => (isFocused ? clearFocus() : setFocus(id))}
            title={isFocused ? 'Свернуть' : 'Развернуть'}
            aria-label={isFocused ? 'Свернуть блок' : 'Развернуть блок'}
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
              aria-label="Закрыть блок"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="block__body">
        <ErrorBoundary>{children}</ErrorBoundary>
      </div>
    </div>
  )
}
