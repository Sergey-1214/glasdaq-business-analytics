import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { BLOCK_REGISTRY } from '../../store/dashboardStore'
import Block from './Block'
import AssistantChat from './AssistantChat'
import AccountBlock from './AccountBlock'
import MetricsBlock from './MetricsBlock'
import ChartsBlock from './ChartsBlock'
import './SortableBlock.css'

const BLOCK_CONTENT = {
  assistant: <AssistantChat />,
  account: <AccountBlock />,
  metrics: <MetricsBlock />,
  charts: <ChartsBlock />,
}

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
    >
      <Block id={id} title={block?.title ?? id} dragListeners={listeners}>
        {children ?? BLOCK_CONTENT[id] ?? (
          <div className="block-placeholder">Содержимое: {block?.title}</div>
        )}
      </Block>
    </div>
  )
}
