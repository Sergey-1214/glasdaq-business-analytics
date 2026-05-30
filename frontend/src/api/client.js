import { useAuthStore } from '../store/authStore'
import { API_URL, parseJsonSafely } from './http'
import { isTokenExpired } from '../utils/auth'

let isRefreshing = false
let refreshQueue = []

function processQueue(error, token = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  refreshQueue = []
}

async function doRefresh(refreshToken) {
  const response = await fetch(`${API_URL}/api/identity/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })

  if (!response.ok) {
    throw new Error('Session expired')
  }

  const json = await parseJsonSafely(response)
  return json?.data
}

export async function apiFetch(path, options = {}) {
  const store = useAuthStore.getState()
  const { token, refreshToken, setTokens, logout } = store
  const isFormDataBody = typeof FormData !== 'undefined' && options.body instanceof FormData

  const makeHeaders = (activeToken) => ({
    ...(isFormDataBody ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers || {}),
    ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
  })

  let currentToken = token

  if (currentToken && isTokenExpired(currentToken)) {
    if (!refreshToken) {
      logout()
      throw new Error('Session expired')
    }

    if (isRefreshing) {
      currentToken = await new Promise((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      })
    } else {
      isRefreshing = true
      try {
        const data = await doRefresh(refreshToken)
        if (!data?.access_token || !data?.refresh_token) {
          throw new Error('Session expired')
        }

        setTokens(data.access_token, data.refresh_token)
        currentToken = data.access_token
        processQueue(null, currentToken)
      } catch (error) {
        processQueue(error)
        logout()
        throw error
      } finally {
        isRefreshing = false
      }
    }
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: makeHeaders(currentToken),
  })

  if (response.status !== 401) {
    return response
  }

  if (!refreshToken) {
    logout()
    throw new Error('Session expired')
  }

  if (isRefreshing) {
    const nextToken = await new Promise((resolve, reject) => {
      refreshQueue.push({ resolve, reject })
    })

    return fetch(`${API_URL}${path}`, {
      ...options,
      headers: makeHeaders(nextToken),
    })
  }

  isRefreshing = true

  try {
    const data = await doRefresh(refreshToken)
    if (!data?.access_token || !data?.refresh_token) {
      throw new Error('Session expired')
    }

    setTokens(data.access_token, data.refresh_token)
    processQueue(null, data.access_token)

    return fetch(`${API_URL}${path}`, {
      ...options,
      headers: makeHeaders(data.access_token),
    })
  } catch (error) {
    processQueue(error)
    logout()
    throw error
  } finally {
    isRefreshing = false
  }
}
