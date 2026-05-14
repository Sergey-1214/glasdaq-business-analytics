import { create } from 'zustand'

let entryId = 0

export const useAnalysisStore = create((set) => ({
  entries: [],
  parsed: null,
  analysis: null,

  addEntry: (ideaText, parsed) => {
    const id = ++entryId
    set((s) => ({
      entries: [...s.entries, { id, ideaText, parsed, analysis: null }],
      parsed,
      analysis: null,
    }))
    return id
  },

  updateEntryAnalysis: (id, analysis) => set((s) => ({
    entries: s.entries.map((e) => (e.id === id ? { ...e, analysis } : e)),
    analysis,
  })),

  setParsed: (parsed) => set({ parsed }),
  setAnalysis: (analysis) => set({ analysis }),

  clear: () => set({ entries: [], parsed: null, analysis: null }),
}))
