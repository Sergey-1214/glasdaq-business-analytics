import { Home } from 'lucide-react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { BLOCK_REGISTRY, useDashboardStore } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import './LeftSidebar.css'

function FocusSidebar() {
  const { zones, focusedBlockId, setFocus, clearFocus } = useDashboardStore()
  const allActiveIds = Object.values(zones).flat()
  const allActiveBlocks = BLOCK_REGISTRY.filter((block) => allActiveIds.includes(block.id))

  return (
    <aside className="left-sidebar left-sidebar--narrow">
      <nav className="left-sidebar__icon-nav">
        <button
          className="left-sidebar__icon-btn left-sidebar__icon-btn--home"
          onClick={clearFocus}
          title="Выйти из режима фокуса"
          aria-label="Выйти из режима фокуса"
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
            aria-label={block.title}
          >
            {block.icon}
          </button>
        ))}
      </nav>
    </aside>
  )
}

function NormalSidebar({ isDropTarget }) {
  const { zones } = useDashboardStore()
  const leftIds = zones.left
  const { setNodeRef } = useDroppable({ id: 'left' })

  return (
    <aside className={`left-sidebar ${isDropTarget ? 'left-sidebar--drop-target' : ''}`}>
      <SortableContext id="left" items={leftIds} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="left-sidebar__blocks">
          {leftIds.map((id) => (
            <SortableBlock key={id} id={id} />
          ))}
        </div>
      </SortableContext>
    </aside>
  )
}

export default function LeftSidebar({ isDropTarget = false }) {
  const { focusedBlockId } = useDashboardStore()
  return focusedBlockId ? <FocusSidebar /> : <NormalSidebar isDropTarget={isDropTarget} />
}
