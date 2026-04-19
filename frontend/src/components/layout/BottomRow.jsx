import { useState, useRef } from 'react'
import { Plus } from 'lucide-react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, horizontalListSortingStrategy } from '@dnd-kit/sortable'
import { useDashboardStore } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import WorkspaceSelector from '../ui/WorkspaceSelector'
import './BottomRow.css'

export default function BottomRow({ isDropTarget = false }) {
  const { zones } = useDashboardStore()
  const bottomIds = zones.bottom
  const { setNodeRef } = useDroppable({ id: 'bottom' })
  const [selectorOpen, setSelectorOpen] = useState(false)
  const addBtnRef = useRef(null)

  return (
    <div className="bottom-row-wrap">
      <SortableContext id="bottom" items={bottomIds} strategy={horizontalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={`bottom-row ${isDropTarget ? 'bottom-row--drop-target' : ''}`}
        >
          {bottomIds.map((id) => (
            <SortableBlock key={id} id={id} className="bottom-row__item" />
          ))}
        </div>
      </SortableContext>

      <div className="bottom-row__add-wrapper">
        <button
          ref={addBtnRef}
          className="bottom-row__add-btn"
          title="Добавить блок"
          onClick={() => setSelectorOpen((v) => !v)}
        >
          <Plus size={18} />
        </button>
        {selectorOpen && (
          <WorkspaceSelector
            triggerRef={addBtnRef}
            onClose={() => setSelectorOpen(false)}
            targetZone="bottom"
            usePortal
          />
        )}
      </div>
    </div>
  )
}
