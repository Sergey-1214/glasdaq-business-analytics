import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { API_URL, parseApiResponse } from '../api/http'

async function apiLogin(email, password) {
  const response = await fetch(`${API_URL}/api/identity/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  return parseApiResponse(response, 'Неверный email или пароль')
}

async function apiRegister(username, email, password) {
  const response = await fetch(`${API_URL}/api/identity/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })

  return parseApiResponse(response, 'Ошибка регистрации')
}

async function apiLogout(refreshToken) {
  try {
    await fetch(`${API_URL}/api/identity/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  } catch {
    // Ignore network errors on logout.
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
        } catch (error) {
          set({ error: error.message, loading: false })
          throw error
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
        } catch (error) {
          set({ error: error.message, loading: false })
          throw error
        }
      },

      setTokens: (token, refreshToken) => set({ token, refreshToken }),

      logout: () => {
        const { refreshToken } = get()
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })

        if (refreshToken) {
          apiLogout(refreshToken)
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'glasdaq-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
