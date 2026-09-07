import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '../App.vue'
import { setupAuthGuard } from '../auth/guard'
import { routes } from '../router'

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

async function mountApp(path: string) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes })
  setupAuthGuard(router)
  router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] } })
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('App shell', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects unauthenticated users to the login page', async () => {
    mockFetch(401)
    const wrapper = await mountApp('/tasks')
    expect(wrapper.text()).toContain('Log in to your account')
  })

  it('shows the tasks view when authenticated', async () => {
    mockFetch(200, USER)
    const wrapper = await mountApp('/tasks')
    expect(wrapper.text()).toContain('The task list lands in M2')
    expect(wrapper.text()).toContain('Calendar')
    expect(wrapper.text()).toContain('Session')
  })

  it('shows the calendar placeholder', async () => {
    mockFetch(200, USER)
    const wrapper = await mountApp('/calendar')
    expect(wrapper.text()).toContain('Timeboxes land in M3')
  })

  it('sends authenticated users away from /login', async () => {
    mockFetch(200, USER)
    const wrapper = await mountApp('/login')
    expect(wrapper.text()).toContain('The task list lands in M2')
  })
})
