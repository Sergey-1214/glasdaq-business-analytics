import { create } from 'zustand'
import { persist } from 'zustand/middleware'

async function apiLogin(email, password) {
  return {
    user: { id: 1, email, name: email.split('@')[0], createdAt: '2025-01-15', plan: 'Pro' },
    access_token: 'mock-token-' + Date.now(),
  }
}

async function apiRegister(name, email, password) {
  const today = new Date().toISOString().slice(0, 10)
  return {
    user: { id: Date.now(), email, name, createdAt: today, plan: 'Basic' },
    access_token: 'mock-token-' + Date.now(),
  }
}

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
      loading: false,

      login: async (email, password) => {
        set({ loading: true, error: null })
        try {
          const data = await apiLogin(email, password)
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            loading: false,
          })
        } catch (e) {
          set({ error: e.message, loading: false })
          throw e
        }
      },

      register: async (name, email, password) => {
        set({ loading: true, error: null })
        try {
          const data = await apiRegister(name, email, password)
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            loading: false,
          })
        } catch (e) {
          set({ error: e.message, loading: false })
          throw e
        }
      },

      logout: () => set({ user: null, token: null, isAuthenticated: false, error: null }),

      clearError: () => set({ error: null }),
    }),
    {
      name: 'glasdaq-auth',
      partialize: (s) => ({ user: s.user, token: s.token, isAuthenticated: s.isAuthenticated }),
    }
  )
)
