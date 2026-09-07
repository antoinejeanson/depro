import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../stores/auth'

const USER = { id: '1', email: 'ada@example.com', created_at: '2025-01-01T00:00:00' }

function mockFetch(status: number, body?: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
}

function freshStore() {
  setActivePinia(createPinia())
  return useAuthStore()
}

describe('auth store', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetchMe stores the user on 200', async () => {
    mockFetch(200, USER)
    const auth = freshStore()
    await auth.fetchMe()
    expect(auth.user?.email).toBe('ada@example.com')
    expect(auth.checked).toBe(true)
  })

  it('fetchMe clears the user on 401 and marks checked', async () => {
    mockFetch(401)
    const auth = freshStore()
    await auth.fetchMe()
    expect(auth.user).toBeNull()
    expect(auth.checked).toBe(true)
  })

  it('login stores the returned user', async () => {
    mockFetch(200, USER)
    const auth = freshStore()
    await auth.login('ada@example.com', 'supersecret1')
    expect(auth.user?.email).toBe('ada@example.com')
    expect(auth.checked).toBe(true)
  })

  it('login propagates API errors', async () => {
    mockFetch(401, { detail: 'Invalid email or password' })
    const auth = freshStore()
    await expect(auth.login('ada@example.com', 'nope')).rejects.toThrow()
    expect(auth.user).toBeNull()
  })

  it('logout clears the user even when the API fails', async () => {
    mockFetch(500)
    const auth = freshStore()
    auth.user = USER
    await auth.logout()
    expect(auth.user).toBeNull()
  })
})
