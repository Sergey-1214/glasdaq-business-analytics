import { create } from 'zustand'

export const useAnalysisStore = create((set) => ({
  parsed: null,
  analysis: null,
  ideaText: null,

  setParsed: (data) => set({ parsed: data }),
  setAnalysis: (data) => set({ analysis: data }),
  setIdeaText: (text) => set({ ideaText: text }),
  clear: () => set({ parsed: null, analysis: null, ideaText: null }),
}))
