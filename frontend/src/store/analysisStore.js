import { create } from 'zustand'

let entryId = 0

export const useAnalysisStore = create((set) => ({
  entries: [],
  parsed: null,
  analysis: null,
  preparedReports: [],

  addEntry: (ideaText, parsed, selectedPoint = null) => {
    const id = ++entryId
    const createdAt = new Date().toISOString()
    set((s) => ({
      entries: [...s.entries, { id, ideaText, parsed, analysis: null, selectedPoint, createdAt }],
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

  prepareReport: (entryId) => set((state) => {
    const existing = state.preparedReports.find((report) => report.entryId === entryId)
    const nextReport = { entryId, generatedAt: new Date().toISOString() }

    return {
      preparedReports: existing
        ? state.preparedReports.map((report) => (report.entryId === entryId ? nextReport : report))
        : [...state.preparedReports, nextReport],
    }
  }),

  removePreparedReport: (entryId) => set((state) => ({
    preparedReports: state.preparedReports.filter((report) => report.entryId !== entryId),
  })),

  clear: () => set({ entries: [], parsed: null, analysis: null, preparedReports: [] }),
}))
