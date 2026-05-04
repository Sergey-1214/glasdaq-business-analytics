import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useDashboardStore, BLOCK_REGISTRY } from '../../store/dashboardStore'
import './WorkspaceSelector.css'

export default function WorkspaceSelector({
  onClose,
  className = '',
  triggerRef = null,
  targetZone = null,
  usePortal = false,
  portalSide = 'up',
}) {
  const { isActive, toggleBlock } = useDashboardStore()
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (triggerRef?.current && triggerRef.current.contains(e.target)) return
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose, triggerRef])

  let portalStyle = {}
  if (usePortal && triggerRef?.current) {
    const rect = triggerRef.current.getBoundingClientRect()
    if (portalSide === 'right') {
      const clampedTop = Math.max(8, Math.min(rect.top, window.innerHeight - 300))
      portalStyle = {
        position: 'fixed',
        top: clampedTop,
        left: rect.right + 8,
        transform: 'none',
        zIndex: 1000,
        maxHeight: window.innerHeight - clampedTop - 8,
        overflowY: 'auto',
      }
    } else {
      portalStyle = {
        position: 'fixed',
        top: 'auto',
        left: 'auto',
        transform: 'none',
        bottom: window.innerHeight - rect.top + 8,
        right: window.innerWidth - rect.right,
        zIndex: 1000,
      }
    }
  }

  const content = (
    <div
      className={`workspace-selector ${className}`}
      ref={ref}
      style={usePortal ? portalStyle : undefined}
    >
      <div className="workspace-selector__header">Блоки рабочей области</div>
      <ul className="workspace-selector__list">
        {BLOCK_REGISTRY.filter((b) => b.id !== 'map').map((block) => (
          <li key={block.id} className="workspace-selector__item">
            <label>
              <input
                type="checkbox"
                checked={isActive(block.id)}
                onChange={() => toggleBlock(block.id, isActive(block.id) ? null : targetZone)}
              />
              <span className="workspace-selector__name">{block.title}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )

  return usePortal ? createPortal(content, document.body) : content
}
