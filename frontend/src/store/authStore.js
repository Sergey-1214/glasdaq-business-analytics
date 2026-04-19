import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ─── MOCK ────────────────────────────────────────────────────────────────────
// Сейчас используется mock-авторизация (любые данные проходят).
// Когда бэкенд будет готов — замени функции login/register согласно инструкции.
// ─────────────────────────────────────────────────────────────────────────────

async function apiLogin(email, password) {
  // ЗАГЛУШКА: убери этот блок и раскомментируй ниже, когда бэкенд будет готов
  return {
    user: { id: 1, email, name: email.split('@')[0] },
    access_token: 'mock-token-' + Date.now(),
  }

  // РЕАЛЬНЫЙ ЗАПРОС (раскомментировать):
  // const res = await fetch('/api/auth/login', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, password }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Неверный email или пароль')
  // }
  // return res.json() // { user, access_token }
}

async function apiRegister(name, email, password) {
  // ЗАГЛУШКА:
  return {
    user: { id: Date.now(), email, name },
    access_token: 'mock-token-' + Date.now(),
  }

  // РЕАЛЬНЫЙ ЗАПРОС (раскомментировать):
  // const res = await fetch('/api/auth/register', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ name, email, password }),
  // })
  // if (!res.ok) {
  //   const err = await res.json().catch(() => ({}))
  //   throw new Error(err.detail || 'Ошибка регистрации')
  // }
  // return res.json() // { user, access_token }
}

// ─────────────────────────────────────────────────────────────────────────────

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
