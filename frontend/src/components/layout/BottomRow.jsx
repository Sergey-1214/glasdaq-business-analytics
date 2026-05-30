import { useDroppable } from '@dnd-kit/core'
import { SortableContext, horizontalListSortingStrategy } from '@dnd-kit/sortable'
import { useDashboardStore } from '../../store/dashboardStore'
import SortableBlock from '../blocks/SortableBlock'
import './BottomRow.css'

export default function BottomRow({ isDropTarget = false }) {
  const { zones } = useDashboardStore()
  const bottomIds = zones.bottom
  const { setNodeRef } = useDroppable({ id: 'bottom' })

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
    </div>
  )
}
