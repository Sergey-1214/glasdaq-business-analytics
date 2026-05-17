import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from './authStore'

const MOCK_USER = {
  id: 'uuid-123',
  username: 'alice',
  email: 'alice@example.com',
  is_active: true,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
  last_login_at: null,
}

const MOCK_AUTH_RESPONSE = {
  data: {
    access_token: 'access-jwt-abc',
    refresh_token: 'refresh-jwt-xyz',
    token_type: 'bearer',
    access_expires_in: 900,
    refresh_expires_in: 2592000,
    user: MOCK_USER,
  },
}

function mockFetchOk(body) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  })
}

function mockFetchFail(status, detail) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({ detail }),
  })
}

function resetStore() {
  useAuthStore.setState({
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    error: null,
    loading: false,
  })
}

describe('useAuthStore', () => {
  beforeEach(() => {
    resetStore()
    useAuthStore.persist?.clearStorage()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('has anonymous initial state', () => {
    const s = useAuthStore.getState()
    expect(s.user).toBeNull()
    expect(s.token).toBeNull()
    expect(s.refreshToken).toBeNull()
    expect(s.isAuthenticated).toBe(false)
    expect(s.error).toBeNull()
    expect(s.loading).toBe(false)
  })

  it('login authenticates user and stores tokens', async () => {
    vi.stubGlobal('fetch', mockFetchOk(MOCK_AUTH_RESPONSE))

    await useAuthStore.getState().login('alice@example.com', 'password123')
    const s = useAuthStore.getState()

    expect(s.isAuthenticated).toBe(true)
    expect(s.loading).toBe(false)
    expect(s.error).toBeNull()
    expect(s.token).toBe('access-jwt-abc')
    expect(s.refreshToken).toBe('refresh-jwt-xyz')
    expect(s.user).toMatchObject({ username: 'alice', email: 'alice@example.com' })
  })

  it('login calls correct endpoint with credentials', async () => {
    const fetchMock = mockFetchOk(MOCK_AUTH_RESPONSE)
    vi.stubGlobal('fetch', fetchMock)

    await useAuthStore.getState().login('alice@example.com', 'password123')

    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/identity/auth/login')
    expect(JSON.parse(opts.body)).toEqual({ email: 'alice@example.com', password: 'password123' })
  })

  it('login sets error and throws on failure', async () => {
    vi.stubGlobal('fetch', mockFetchFail(401, 'invalid credentials'))

    await expect(
      useAuthStore.getState().login('wrong@example.com', 'bad')
    ).rejects.toThrow('invalid credentials')

    const s = useAuthStore.getState()
    expect(s.isAuthenticated).toBe(false)
    expect(s.error).toBe('invalid credentials')
    expect(s.loading).toBe(false)
  })

  it('register authenticates new user', async () => {
    vi.stubGlobal('fetch', mockFetchOk({ ...MOCK_AUTH_RESPONSE, status: 201 }))

    await useAuthStore.getState().register('alice', 'alice@example.com', 'password123')
    const s = useAuthStore.getState()

    expect(s.isAuthenticated).toBe(true)
    expect(s.token).toBe('access-jwt-abc')
    expect(s.user.username).toBe('alice')
  })

  it('register calls correct endpoint with username', async () => {
    const fetchMock = mockFetchOk(MOCK_AUTH_RESPONSE)
    vi.stubGlobal('fetch', fetchMock)

    await useAuthStore.getState().register('alice', 'alice@example.com', 'password123')

    const [url, opts] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/identity/auth/register')
    expect(JSON.parse(opts.body)).toEqual({
      username: 'alice',
      email: 'alice@example.com',
      password: 'password123',
    })
  })

  it('logout clears auth state immediately', async () => {
    vi.stubGlobal('fetch', mockFetchOk(MOCK_AUTH_RESPONSE))
    await useAuthStore.getState().login('alice@example.com', 'password123')

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }))
    useAuthStore.getState().logout()

    const s = useAuthStore.getState()
    expect(s.user).toBeNull()
    expect(s.token).toBeNull()
    expect(s.refreshToken).toBeNull()
    expect(s.isAuthenticated).toBe(false)
  })

  it('setTokens updates token and refreshToken', () => {
    useAuthStore.getState().setTokens('new-access', 'new-refresh')
    const s = useAuthStore.getState()
    expect(s.token).toBe('new-access')
    expect(s.refreshToken).toBe('new-refresh')
  })

  it('clearError removes error value', () => {
    useAuthStore.setState({ error: 'boom' })
    useAuthStore.getState().clearError()
    expect(useAuthStore.getState().error).toBeNull()
  })
})
