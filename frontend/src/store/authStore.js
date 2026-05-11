import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function parseResponse(res, fallbackError) {
  let json
  try {
    json = await res.json()
  } catch {
    throw new Error(`Ошибка сервера (${res.status})`)
  }
  if (!res.ok) {
    const detail = json.detail
    if (Array.isArray(detail)) throw new Error(detail[0]?.msg || fallbackError)
    throw new Error(typeof detail === 'string' ? detail : fallbackError)
  }
  return json.data
}

async function apiLogin(email, password) {
  const res = await fetch(`${API_URL}/api/identity/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return parseResponse(res, 'Неверный email или пароль')
}

async function apiRegister(username, email, password) {
  const res = await fetch(`${API_URL}/api/identity/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
  return parseResponse(res, 'Ошибка регистрации')
}

async function apiLogout(refreshToken) {
  try {
    await fetch(`${API_URL}/api/identity/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } catch {
    // ignore network errors on logout
  }
}

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
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
            refreshToken: data.refresh_token,
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
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            loading: false,
          })
        } catch (e) {
          set({ error: e.message, loading: false })
          throw e
        }
      },

      setTokens: (token, refreshToken) => set({ token, refreshToken }),

      logout: () => {
        const { refreshToken } = get()
        set({ user: null, token: null, refreshToken: null, isAuthenticated: false, error: null })
        if (refreshToken) apiLogout(refreshToken)
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'glasdaq-auth',
      partialize: (s) => ({
        user: s.user,
        token: s.token,
        refreshToken: s.refreshToken,
        isAuthenticated: s.isAuthenticated,
      }),
    }
  )
)
