import { beforeEach, describe, expect, it } from 'vitest'

import { useDashboardStore } from './dashboardStore'

const INITIAL_ZONES = {
  left: ['account', 'actions'],
  center: ['map'],
  right: ['assistant'],
  bottom: ['charts', 'reports', 'metrics'],
}

function resetDashboardStore() {
  useDashboardStore.setState({
    zones: {
      left: [...INITIAL_ZONES.left],
      center: [...INITIAL_ZONES.center],
      right: [...INITIAL_ZONES.right],
      bottom: [...INITIAL_ZONES.bottom],
    },
    focusedBlockId: null,
  })
}

describe('useDashboardStore', () => {
  beforeEach(() => {
    resetDashboardStore()
  })

  it('detects active and inactive blocks', () => {
    const { isActive } = useDashboardStore.getState()

    expect(isActive('map')).toBe(true)
    expect(isActive('unknown')).toBe(false)
  })

  it('toggleBlock removes existing block from its zone', () => {
    useDashboardStore.getState().toggleBlock('actions')
    const { zones } = useDashboardStore.getState()

    expect(zones.left).toEqual(['account'])
  })

  it('toggleBlock adds missing block to explicit target zone', () => {
    useDashboardStore.getState().toggleBlock('actions')
    useDashboardStore.getState().toggleBlock('actions', 'right')
    const { zones } = useDashboardStore.getState()

    expect(zones.right).toContain('actions')
  })

  it('toggleBlock clears focus when focused block is removed', () => {
    useDashboardStore.setState({ focusedBlockId: 'actions' })

    useDashboardStore.getState().toggleBlock('actions')

    expect(useDashboardStore.getState().focusedBlockId).toBeNull()
  })

  it('reorderZone reorders blocks inside a zone', () => {
    useDashboardStore.getState().reorderZone('bottom', 0, 2)
    const { bottom } = useDashboardStore.getState().zones

    expect(bottom).toEqual(['reports', 'metrics', 'charts'])
  })

  it('moveBlock moves block between zones at explicit index', () => {
    useDashboardStore.getState().moveBlock('actions', 'left', 'right', 0)
    const { left, right } = useDashboardStore.getState().zones

    expect(left).toEqual(['account'])
    expect(right).toEqual(['actions', 'assistant'])
  })

  it('moveBlock appends block when index is negative', () => {
    useDashboardStore.getState().moveBlock('actions', 'left', 'right', -1)
    const { right } = useDashboardStore.getState().zones

    expect(right).toEqual(['assistant', 'actions'])
  })

  it('setFocus and clearFocus update focusedBlockId', () => {
    useDashboardStore.getState().setFocus('map')
    expect(useDashboardStore.getState().focusedBlockId).toBe('map')

    useDashboardStore.getState().clearFocus()
    expect(useDashboardStore.getState().focusedBlockId).toBeNull()
  })
})
