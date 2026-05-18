import { useState } from 'react'
import {
  DndContext,
  DragOverlay,
  pointerWithin,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { useDashboardStore, BLOCK_REGISTRY } from './store/dashboardStore'
import TopBar from './components/layout/TopBar'
import LeftSidebar from './components/layout/LeftSidebar'
import RightSidebar from './components/layout/RightSidebar'
import BottomRow from './components/layout/BottomRow'
import Block from './components/blocks/Block'
import AssistantChat from './components/blocks/AssistantChat'
import AccountBlock from './components/blocks/AccountBlock'
import MetricsBlock from './components/blocks/MetricsBlock'
import ChartsBlock from './components/blocks/ChartsBlock'
import ReportsBlock from './components/blocks/ReportsBlock'
import MapBlock from './components/blocks/MapBlock'
import './App.css'

const BLOCK_CONTENT = {
  map: <MapBlock />,
  assistant: <AssistantChat />,
  account: <AccountBlock />,
  metrics: <MetricsBlock />,
  charts: <ChartsBlock />,
  reports: <ReportsBlock />,
}

const DROPPABLE_ZONES = ['left', 'right', 'bottom']

function collisionDetection(args) {
  const pointerCollisions = pointerWithin(args)
  if (pointerCollisions.length > 0) return pointerCollisions
  return closestCenter(args)
}

function MapArea() {
  const { zones } = useDashboardStore()
  const isMapActive = zones.center.includes('map')
  const block = BLOCK_REGISTRY.find((b) => b.id === 'map')

  return (
    <div className="map-area">
      {isMapActive && (
        <Block id="map" title={block.title} className="map-area__block">
          <MapBlock />
        </Block>
      )}
    </div>
  )
}

function FocusArea() {
  const { focusedBlockId } = useDashboardStore()
  const block = BLOCK_REGISTRY.find((b) => b.id === focusedBlockId)
  if (!block) return null

  return (
    <div className="focus-area">
      <Block id={block.id} title={block.title} className="focus-area__block">
        {BLOCK_CONTENT[block.id] ?? (
          <div className="block-placeholder">Содержимое: {block.title}</div>
        )}
      </Block>
    </div>
  )
}

export default function App() {
  const { zones, focusedBlockId, reorderZone, moveBlock } = useDashboardStore()
  const isFocusMode = focusedBlockId !== null

  const [activeId, setActiveId] = useState(null)
  const [dragOverZone, setDragOverZone] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  function handleDragStart({ active }) {
    setActiveId(String(active.id))
  }

  function handleDragOver({ active, over }) {
    if (!over) {
      setDragOverZone(null)
      return
    }

    const { zones: currentZones } = useDashboardStore.getState()
    const aId = String(active.id)
    const oId = String(over.id)

    const findZone = (id) =>
      Object.entries(currentZones).find(([, ids]) => ids.includes(id))?.[0]

    const sourceZone = findZone(aId)
    const destZone = DROPPABLE_ZONES.includes(oId) ? oId : findZone(oId)

    setDragOverZone(destZone && destZone !== sourceZone ? destZone : null)
  }

  function handleDragEnd({ active, over }) {
    setActiveId(null)
    setDragOverZone(null)

    if (!over) return

    const activeId = String(active.id)
    const overId = String(over.id)

    const findZone = (id) =>
      Object.entries(zones).find(([, ids]) => ids.includes(id))?.[0]

    const sourceZone = findZone(activeId)
    if (!sourceZone) return

    if (DROPPABLE_ZONES.includes(overId)) {
      if (sourceZone !== overId) {
        moveBlock(activeId, sourceZone, overId, zones[overId].length)
      }
      return
    }

    const destZone = findZone(overId)
    if (!destZone) return

    if (sourceZone === destZone) {
      const oldIndex = zones[sourceZone].indexOf(activeId)
      const newIndex = zones[sourceZone].indexOf(overId)
      if (oldIndex !== newIndex) reorderZone(sourceZone, oldIndex, newIndex)
    } else {
      const overIndex = zones[destZone].indexOf(overId)
      moveBlock(activeId, sourceZone, destZone, overIndex)
    }
  }

  function handleDragCancel() {
    setActiveId(null)
    setDragOverZone(null)
  }

  const activeBlock = activeId
    ? BLOCK_REGISTRY.find((b) => b.id === activeId)
    : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collisionDetection}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className={`dashboard ${isFocusMode ? 'dashboard--focus' : ''}`}>
        <TopBar />
        <LeftSidebar isDropTarget={dragOverZone === 'left'} />
        {isFocusMode ? (
          <FocusArea />
        ) : (
          <>
            <main className="dashboard__main">
              <MapArea />
              <BottomRow isDropTarget={dragOverZone === 'bottom'} />
            </main>
            <RightSidebar isDropTarget={dragOverZone === 'right'} />
          </>
        )}
      </div>

      <DragOverlay>
        {activeBlock ? (
          <div className="drag-overlay-block" style={{ pointerEvents: 'none' }}>
            <Block id={activeBlock.id} title={activeBlock.title}>
              <div className="block-placeholder">Содержимое: {activeBlock.title}</div>
            </Block>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
