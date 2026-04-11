import { create } from 'zustand'

export const BLOCK_REGISTRY = [
  { id: 'map',       title: 'Карта',           zone: 'center', icon: '⊕' },
  { id: 'assistant', title: 'Ассистент',        zone: 'right',  icon: '◆' },
  { id: 'charts',    title: 'Графики',          zone: 'bottom', icon: '∿' },
  { id: 'reports',   title: 'Отчёты',           zone: 'bottom', icon: '≡' },
  { id: 'metrics',   title: 'Метрики',          zone: 'bottom', icon: '▦' },
  { id: 'account',   title: 'Аккаунт',          zone: 'left',   icon: '◉' },
  { id: 'actions',   title: 'Быстрые действия', zone: 'left',   icon: '▶' },
]

export const useDashboardStore = create((set, get) => ({
  zones: {
    left:   ['account', 'actions'],
    center: ['map'],
    right:  ['assistant'],
    bottom: ['charts', 'reports', 'metrics'],
  },

  focusedBlockId: null,

  // Проверить активен ли блок (есть ли в любой зоне)
  isActive: (id) => {
    const { zones } = get()
    return Object.values(zones).some((arr) => arr.includes(id))
  },

  // Добавить/убрать блок.
  // targetZone — зона для добавления; если не передана, ищет самую свободную (кроме center).
  toggleBlock: (id, targetZone = null) => set((state) => {
    const currentZone = Object.entries(state.zones)
      .find(([, ids]) => ids.includes(id))?.[0]

    if (currentZone) {
      return {
        zones: {
          ...state.zones,
          [currentZone]: state.zones[currentZone].filter((b) => b !== id),
        },
        focusedBlockId: state.focusedBlockId === id ? null : state.focusedBlockId,
      }
    }

    // Определяем зону для добавления
    let addToZone
    if (targetZone) {
      addToZone = targetZone
    } else {
      // Самая свободная зона (исключая center)
      const candidates = ['left', 'right', 'bottom']
      addToZone = candidates.reduce((min, z) =>
        state.zones[z].length < state.zones[min].length ? z : min
      )
    }

    return {
      zones: {
        ...state.zones,
        [addToZone]: [...state.zones[addToZone], id],
      },
    }
  }),

  // Перестановка блоков внутри одной зоны
  reorderZone: (zone, oldIndex, newIndex) => set((state) => {
    const arr = [...state.zones[zone]]
    const [item] = arr.splice(oldIndex, 1)
    arr.splice(newIndex, 0, item)
    return { zones: { ...state.zones, [zone]: arr } }
  }),

  // Перемещение блока в другую зону
  moveBlock: (id, fromZone, toZone, toIndex) => set((state) => {
    const fromArr = state.zones[fromZone].filter((b) => b !== id)
    const toArr = [...state.zones[toZone]]
    const insertAt = toIndex >= 0 ? toIndex : toArr.length
    toArr.splice(insertAt, 0, id)
    return {
      zones: {
        ...state.zones,
        [fromZone]: fromArr,
        [toZone]: toArr,
      },
    }
  }),

  setFocus: (id) => set({ focusedBlockId: id }),
  clearFocus: () => set({ focusedBlockId: null }),
}))
