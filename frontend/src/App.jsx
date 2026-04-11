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
import './App.css'

const DROPPABLE_ZONES = ['left', 'right', 'bottom']

// pointerWithin точнее для контейнеров, closestCenter — запасной вариант
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
          <div className="map-placeholder">Здесь будет карта (react-leaflet)</div>
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
        <div className="block-placeholder">Содержимое: {block.title}</div>
      </Block>
    </div>
  )
}

export default function App() {
  const { zones, focusedBlockId, reorderZone, moveBlock } = useDashboardStore()
  const isFocusMode = focusedBlockId !== null

  // id блока, который сейчас тащат (для DragOverlay)
  const [activeId, setActiveId] = useState(null)
  // зона, над которой висит блок из ДРУГОЙ зоны (для подсветки)
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

    // Берём свежее состояние стора, чтобы не было stale-closure
    const { zones: currentZones } = useDashboardStore.getState()
    const aId = String(active.id)
    const oId = String(over.id)

    const findZone = (id) =>
      Object.entries(currentZones).find(([, ids]) => ids.includes(id))?.[0]

    const sourceZone = findZone(aId)
    const destZone = DROPPABLE_ZONES.includes(oId) ? oId : findZone(oId)

    // Подсвечиваем только если тащим в ДРУГУЮ зону
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

    // Бросили на контейнер зоны (пустое место)
    if (DROPPABLE_ZONES.includes(overId)) {
      if (sourceZone !== overId) {
        moveBlock(activeId, sourceZone, overId, zones[overId].length)
      }
      return
    }

    // Бросили на конкретный блок
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

      {/* DragOverlay: рендерится поверх всего через портал, не клипается */}
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
