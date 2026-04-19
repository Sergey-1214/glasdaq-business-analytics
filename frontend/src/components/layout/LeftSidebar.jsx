import { useState, useRef } from 'react'
import { Home, Plus } from 'lucide-react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useDashboardStore, BLOCK_REGISTRY } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import WorkspaceSelector from '../ui/WorkspaceSelector'
import './LeftSidebar.css'

// Режим фокуса: узкий сайдбар с иконками всех активных блоков
function FocusSidebar() {
  const { zones, focusedBlockId, setFocus, clearFocus } = useDashboardStore()
  const allActiveIds = Object.values(zones).flat()
  const allActiveBlocks = BLOCK_REGISTRY.filter((b) => allActiveIds.includes(b.id))

  return (
    <aside className="left-sidebar left-sidebar--narrow">
      <nav className="left-sidebar__icon-nav">
        <button
          className="left-sidebar__icon-btn left-sidebar__icon-btn--home"
          onClick={clearFocus}
          title="Выйти из режима фокуса"
        >
          <Home size={16} />
        </button>
        <div className="left-sidebar__icon-divider" />
        {allActiveBlocks.map((block) => (
          <button
            key={block.id}
            className={`left-sidebar__icon-btn ${block.id === focusedBlockId ? 'left-sidebar__icon-btn--active' : ''}`}
            onClick={() => setFocus(block.id)}
            title={block.title}
          >
            {block.icon}
          </button>
        ))}
      </nav>
    </aside>
  )
}

// Обычный режим: блоки левой зоны, перетаскиваемые
function NormalSidebar({ isDropTarget }) {
  const { zones } = useDashboardStore()
  const leftIds = zones.left
  const { setNodeRef } = useDroppable({ id: 'left' })
  const [selectorOpen, setSelectorOpen] = useState(false)
  const addBtnRef = useRef(null)

  return (
    <aside className={`left-sidebar ${isDropTarget ? 'left-sidebar--drop-target' : ''}`}>
      <SortableContext id="left" items={leftIds} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="left-sidebar__blocks">
          {leftIds.map((id) => (
            <SortableBlock key={id} id={id} />
          ))}
        </div>
      </SortableContext>

      <div className="left-sidebar__add-wrapper">
        <button
          ref={addBtnRef}
          className="left-sidebar__add-btn"
          title="Добавить блок"
          onClick={() => setSelectorOpen((v) => !v)}
        >
          <Plus size={18} />
        </button>
        {selectorOpen && (
          <WorkspaceSelector
            triggerRef={addBtnRef}
            onClose={() => setSelectorOpen(false)}
            targetZone="left"
            usePortal
            portalSide="right"
          />
        )}
      </div>
    </aside>
  )
}

export default function LeftSidebar({ isDropTarget = false }) {
  const { focusedBlockId } = useDashboardStore()
  return focusedBlockId ? <FocusSidebar /> : <NormalSidebar isDropTarget={isDropTarget} />
}
