import { useAuthStore } from '../store/authStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let isRefreshing = false
let refreshQueue = []

function processQueue(error, token = null) {
  refreshQueue.forEach(({ resolve, reject }) => error ? reject(error) : resolve(token))
  refreshQueue = []
}

function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

async function doRefresh(refreshToken) {
  const res = await fetch(`${API_URL}/api/identity/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) throw new Error('Session expired')
  const json = await res.json()
  return json.data
}

export async function apiFetch(path, options = {}) {
  const store = useAuthStore.getState()
  const { token, refreshToken, setTokens, logout } = store

  const makeHeaders = (t) => ({
    'Content-Type': 'application/json',
    ...options.headers,
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
  })

  let currentToken = token

  if (currentToken && isTokenExpired(currentToken)) {
    if (!refreshToken) {
      logout()
      throw new Error('Session expired')
    }

    if (isRefreshing) {
      currentToken = await new Promise((resolve, reject) =>
        refreshQueue.push({ resolve, reject })
      )
    } else {
      isRefreshing = true
      try {
        const data = await doRefresh(refreshToken)
        setTokens(data.access_token, data.refresh_token)
        currentToken = data.access_token
        processQueue(null, currentToken)
      } catch (e) {
        processQueue(e)
        logout()
        throw e
      } finally {
        isRefreshing = false
      }
    }
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: makeHeaders(currentToken),
  })

  if (res.status === 401) {
    if (!refreshToken) {
      logout()
      throw new Error('Session expired')
    }

    if (isRefreshing) {
      const newToken = await new Promise((resolve, reject) =>
        refreshQueue.push({ resolve, reject })
      )
      return fetch(`${API_URL}${path}`, {
        ...options,
        headers: makeHeaders(newToken),
      })
    }

    isRefreshing = true
    try {
      const data = await doRefresh(refreshToken)
      setTokens(data.access_token, data.refresh_token)
      const newToken = data.access_token
      processQueue(null, newToken)
      return fetch(`${API_URL}${path}`, {
        ...options,
        headers: makeHeaders(newToken),
      })
    } catch (e) {
      processQueue(e)
      logout()
      throw e
    } finally {
      isRefreshing = false
    }
  }

  return res
}
