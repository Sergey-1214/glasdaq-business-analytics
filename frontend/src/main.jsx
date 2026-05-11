import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AuthPage from './components/auth/AuthPage'
import App from './App.jsx'
import './index.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, token, refreshToken, setTokens, logout } = useAuthStore()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setChecking(false)
      return
    }

    if (!isTokenExpired(token)) {
      setChecking(false)
      return
    }

    if (!refreshToken) {
      logout()
      setChecking(false)
      return
    }

    fetch(`${API_URL}/api/identity/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((json) => setTokens(json.data.access_token, json.data.refresh_token))
      .catch(() => logout())
      .finally(() => setChecking(false))
  }, [])

  if (checking) return null

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function Root() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <App />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
