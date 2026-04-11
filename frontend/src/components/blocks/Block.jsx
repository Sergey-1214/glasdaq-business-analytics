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
            <img
              src={isFocused ? '/shrink.png' : '/expand.png'}
              alt={isFocused ? 'Свернуть' : 'Развернуть'}
            />
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
              <img src="/close.png" alt="Закрыть" />
            </button>
          )}
        </div>
      </div>
      <div className="block__body">{children}</div>
    </div>
  )
}
