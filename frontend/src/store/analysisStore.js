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

  hydrateEntries: (entries) => set(() => {
    const normalizedEntries = [...entries]
      .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt))

    const latestEntry = normalizedEntries[normalizedEntries.length - 1] ?? null

    return {
      entries: normalizedEntries,
      parsed: latestEntry?.parsed ?? null,
      analysis: latestEntry?.analysis ?? null,
      preparedReports: [],
    }
  }),

  replaceEntry: (id, nextEntry) => set((state) => {
    const nextEntries = state.entries.map((entry) => (entry.id === id ? nextEntry : entry))
    const latestEntry = nextEntries[nextEntries.length - 1] ?? null

    return {
      entries: nextEntries,
      parsed: latestEntry?.parsed ?? state.parsed,
      analysis: latestEntry?.analysis ?? state.analysis,
    }
  }),

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
