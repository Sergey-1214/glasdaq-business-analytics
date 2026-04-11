import { useState, useRef } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useDashboardStore } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import WorkspaceSelector from '../ui/WorkspaceSelector'
import './RightSidebar.css'

export default function RightSidebar({ isDropTarget = false }) {
  const { zones } = useDashboardStore()
  const rightIds = zones.right
  const { setNodeRef } = useDroppable({ id: 'right' })
  const [selectorOpen, setSelectorOpen] = useState(false)
  const addBtnRef = useRef(null)

  return (
    <aside className={`right-sidebar ${isDropTarget ? 'right-sidebar--drop-target' : ''}`}>
      <SortableContext id="right" items={rightIds} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="right-sidebar__blocks">
          {rightIds.map((id) => (
            <SortableBlock key={id} id={id} />
          ))}
        </div>
      </SortableContext>

      <div className="right-sidebar__add-wrapper">
        <button
          ref={addBtnRef}
          className="right-sidebar__add-btn"
          title="Добавить блок"
          onClick={() => setSelectorOpen((v) => !v)}
        >
          +
        </button>
        {selectorOpen && (
          <WorkspaceSelector
            triggerRef={addBtnRef}
            onClose={() => setSelectorOpen(false)}
            className="workspace-selector--from-right-sidebar"
            targetZone="right"
          />
        )}
      </div>
    </aside>
  )
}
