import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import App from './App'
import AuthPage from './components/auth/AuthPage'
import { API_URL, parseJsonSafely } from './api/http'
import { useAuthStore } from './store/authStore'
import { isTokenExpired } from './utils/auth'

function ProtectedRoute({ children }) {
  const { isAuthenticated, token, refreshToken, setTokens, logout } = useAuthStore()
  const [checking, setChecking] = useState(() => isAuthenticated && Boolean(token))

  useEffect(() => {
    let cancelled = false

    async function ensureSession() {
      if (!isAuthenticated || !token) {
        if (!cancelled) setChecking(false)
        return
      }

      if (!isTokenExpired(token)) {
        if (!cancelled) setChecking(false)
        return
      }

      if (!refreshToken) {
        logout()
        if (!cancelled) setChecking(false)
        return
      }

      try {
        const response = await fetch(`${API_URL}/api/identity/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        const json = await parseJsonSafely(response)

        if (!response.ok || !json?.data?.access_token || !json?.data?.refresh_token) {
          throw new Error('refresh_failed')
        }

        setTokens(json.data.access_token, json.data.refresh_token)
      } catch {
        logout()
      } finally {
        if (!cancelled) setChecking(false)
      }
    }

    ensureSession()

    return () => {
      cancelled = true
    }
  }, [isAuthenticated, logout, refreshToken, setTokens, token])

  if (checking) {
    return <div className="app-loader" aria-live="polite">Загрузка...</div>
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function Root() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route
          path="/*"
          element={(
            <ProtectedRoute>
              <App />
            </ProtectedRoute>
          )}
        />
      </Routes>
    </BrowserRouter>
  )
}
