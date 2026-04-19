import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { BLOCK_REGISTRY } from '../../store/dashboardStore'
import Block from './Block'
import AssistantChat from './AssistantChat'
import './SortableBlock.css'

const BLOCK_CONTENT = {
  assistant: <AssistantChat />,
}

/**
 * Обёртка для Block с поддержкой drag-and-drop.
 * Используется во всех зонах: left, right, bottom.
 * className — дополнительный класс для управления размером в контексте зоны.
 */
export default function SortableBlock({ id, className = '', children }) {
  const block = BLOCK_REGISTRY.find((b) => b.id === id)

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  // Когда блок тащат — оставляем "слот" почти невидимым,
  // реальный визуал показывает DragOverlay в App.jsx
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.15 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`sortable-block ${className}`}
      {...attributes}
      {...listeners}
    >
      <Block id={id} title={block?.title ?? id}>
        {children ?? BLOCK_CONTENT[id] ?? (
          <div className="block-placeholder">Содержимое: {block?.title}</div>
        )}
      </Block>
    </div>
  )
}
