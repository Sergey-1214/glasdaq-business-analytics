import { create } from 'zustand'

let msgId = 0

export const useChatStore = create((set) => ({
  messages: [
    { id: ++msgId, role: 'assistant', text: 'Опишите вашу бизнес-идею — я проанализирую рынок, аудиторию и конкурентов.' },
  ],
  loading: false,
  playedIds: new Set(),

  addMessage: (role, text) => {
    const id = ++msgId
    set((s) => ({ messages: [...s.messages, { id, role, text }] }))
    return id
  },

  updateMessage: (id, text) =>
    set((s) => ({
      messages: s.messages.map((m) => m.id === id ? { ...m, text } : m),
      playedIds: (() => { const p = new Set(s.playedIds); p.delete(id); return p })(),
    })),

  setLoading: (loading) => set({ loading }),

  markPlayed: (id) =>
    set((s) => ({ playedIds: new Set([...s.playedIds, id]) })),
}))
