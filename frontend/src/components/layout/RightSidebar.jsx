import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useDashboardStore } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import './RightSidebar.css'

export default function RightSidebar({ isDropTarget = false }) {
  const { zones } = useDashboardStore()
  const rightIds = zones.right
  const { setNodeRef } = useDroppable({ id: 'right' })

  return (
    <aside className={`right-sidebar ${isDropTarget ? 'right-sidebar--drop-target' : ''}`}>
      <SortableContext id="right" items={rightIds} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="right-sidebar__blocks">
          {rightIds.map((id) => (
            <SortableBlock key={id} id={id} />
          ))}
        </div>
      </SortableContext>
    </aside>
  )
}
