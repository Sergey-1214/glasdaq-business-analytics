import { create } from 'zustand'

let entryId = 0

export const useAnalysisStore = create((set) => ({
  entries: [],

  addEntry: (ideaText, parsed) => {
    const id = ++entryId
    set((s) => ({ entries: [...s.entries, { id, ideaText, parsed, analysis: null }] }))
    return id
  },

  updateEntryAnalysis: (id, analysis) => set((s) => ({
    entries: s.entries.map((e) => (e.id === id ? { ...e, analysis } : e)),
  })),

  clear: () => set({ entries: [] }),
}))
