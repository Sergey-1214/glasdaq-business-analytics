import { create } from 'zustand'

export const useLocationStore = create((set) => ({
  selectedPoint: null,

  setSelectedPoint: (coordinates) => set({ selectedPoint: coordinates }),
  clearSelectedPoint: () => set({ selectedPoint: null }),
}))
