import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from './authStore'

function resetAuthStore() {
  useAuthStore.setState({
    user: null,
    token: null,
    isAuthenticated: false,
    error: null,
    loading: false,
  })
}

describe('useAuthStore', () => {
  beforeEach(() => {
    resetAuthStore()
    useAuthStore.persist?.clearStorage()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('has anonymous initial state', () => {
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.error).toBeNull()
    expect(state.loading).toBe(false)
  })

  it('login authenticates user and stores token', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(1700000000000)

    await useAuthStore.getState().login('user@example.com', 'secret123')
    const state = useAuthStore.getState()

    expect(state.isAuthenticated).toBe(true)
    expect(state.loading).toBe(false)
    expect(state.token).toBe('mock-token-1700000000000')
    expect(state.user).toMatchObject({
      email: 'user@example.com',
      name: 'user',
      plan: 'Pro',
    })
  })

  it('register authenticates new user', async () => {
    vi.spyOn(Date, 'now').mockReturnValue(1700000001234)

    await useAuthStore.getState().register('Alice', 'alice@example.com', 'secret123')
    const state = useAuthStore.getState()

    expect(state.isAuthenticated).toBe(true)
    expect(state.loading).toBe(false)
    expect(state.token).toBe('mock-token-1700000001234')
    expect(state.user).toMatchObject({
      id: 1700000001234,
      email: 'alice@example.com',
      name: 'Alice',
      plan: 'Basic',
    })
  })

  it('logout clears auth data', async () => {
    await useAuthStore.getState().login('user@example.com', 'secret123')

    useAuthStore.getState().logout()
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.error).toBeNull()
  })

  it('clearError removes error value', () => {
    useAuthStore.setState({ error: 'boom' })

    useAuthStore.getState().clearError()

    expect(useAuthStore.getState().error).toBeNull()
  })
})
