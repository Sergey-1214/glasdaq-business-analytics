import { create } from 'zustand'

export const BLOCK_REGISTRY = [
  { id: 'map', title: 'Карта', zone: 'center', icon: '⊕' },
  { id: 'assistant', title: 'Ассистент', zone: 'right', icon: '◆' },
  { id: 'charts', title: 'Графики', zone: 'bottom', icon: '∿' },
  { id: 'reports', title: 'Отчеты', zone: 'bottom', icon: '≡' },
  { id: 'metrics', title: 'Метрики', zone: 'bottom', icon: '▦' },
  { id: 'account', title: 'Аккаунт', zone: 'left', icon: '◉' },
]

export const useDashboardStore = create((set, get) => ({
  zones: {
    left: ['account'],
    center: ['map'],
    right: ['assistant'],
    bottom: ['charts', 'reports', 'metrics'],
  },

  focusedBlockId: null,

  isActive: (id) => {
    const { zones } = get()
    return Object.values(zones).some((ids) => ids.includes(id))
  },

  toggleBlock: (id, targetZone = null) =>
    set((state) => {
      const currentZone = Object.entries(state.zones).find(([, ids]) => ids.includes(id))?.[0]

      if (currentZone) {
        return {
          zones: {
            ...state.zones,
            [currentZone]: state.zones[currentZone].filter((blockId) => blockId !== id),
          },
          focusedBlockId: state.focusedBlockId === id ? null : state.focusedBlockId,
        }
      }

      let addToZone
      if (targetZone) {
        addToZone = targetZone
      } else {
        const candidates = ['left', 'right', 'bottom']
        addToZone = candidates.reduce((minZone, zone) =>
          state.zones[zone].length < state.zones[minZone].length ? zone : minZone,
        )
      }

      return {
        zones: {
          ...state.zones,
          [addToZone]: [...state.zones[addToZone], id],
        },
      }
    }),

  reorderZone: (zone, oldIndex, newIndex) =>
    set((state) => {
      const nextItems = [...state.zones[zone]]
      const [item] = nextItems.splice(oldIndex, 1)
      nextItems.splice(newIndex, 0, item)
      return { zones: { ...state.zones, [zone]: nextItems } }
    }),

  moveBlock: (id, fromZone, toZone, toIndex) =>
    set((state) => {
      const fromItems = state.zones[fromZone].filter((blockId) => blockId !== id)
      const toItems = [...state.zones[toZone]]
      const insertAt = toIndex >= 0 ? toIndex : toItems.length
      toItems.splice(insertAt, 0, id)

      return {
        zones: {
          ...state.zones,
          [fromZone]: fromItems,
          [toZone]: toItems,
        },
      }
    }),

  setFocus: (id) => set({ focusedBlockId: id }),
  clearFocus: () => set({ focusedBlockId: null }),
}))
