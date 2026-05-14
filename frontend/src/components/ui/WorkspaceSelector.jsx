import { useEffect, useLayoutEffect, useRef, useState } from 'react'
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
  const [portalStyle, setPortalStyle] = useState({})

  useEffect(() => {
    function handleClick(e) {
      if (triggerRef?.current && triggerRef.current.contains(e.target)) return
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }

    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose, triggerRef])

  useLayoutEffect(() => {
    if (!usePortal || !triggerRef?.current) return

    function updatePosition() {
      const rect = triggerRef.current?.getBoundingClientRect()
      if (!rect) return

      if (portalSide === 'right') {
        const clampedTop = Math.max(8, Math.min(rect.top, window.innerHeight - 300))
        setPortalStyle({
          position: 'fixed',
          top: clampedTop,
          left: Math.min(rect.right + 8, window.innerWidth - 280),
          transform: 'none',
          zIndex: 1000,
          maxHeight: window.innerHeight - clampedTop - 8,
          overflowY: 'auto',
        })
        return
      }

      setPortalStyle({
        position: 'fixed',
        top: 'auto',
        left: 'auto',
        transform: 'none',
        bottom: window.innerHeight - rect.top + 8,
        right: Math.max(8, window.innerWidth - rect.right),
        zIndex: 1000,
      })
    }

    const frameId = window.requestAnimationFrame(updatePosition)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [portalSide, triggerRef, usePortal])

  const content = (
    <div
      className={`workspace-selector ${className}`}
      ref={ref}
      style={usePortal ? portalStyle : undefined}
      role="dialog"
      aria-label="Выбор блоков рабочей области"
    >
      <div className="workspace-selector__header">Блоки рабочей области</div>
      <ul className="workspace-selector__list">
        {BLOCK_REGISTRY.filter((block) => block.id !== 'map').map((block) => {
          const active = isActive(block.id)

          return (
            <li key={block.id} className="workspace-selector__item">
              <label>
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => toggleBlock(block.id, active ? null : targetZone)}
                />
                <span className="workspace-selector__name">{block.title}</span>
              </label>
            </li>
          )
        })}
      </ul>
    </div>
  )

  return usePortal ? createPortal(content, document.body) : content
}
