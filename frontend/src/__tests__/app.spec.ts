import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '../App.vue'
import { setupAuthGuard } from '../auth/guard'
import { routes } from '../router'

const USER = { id: '1', email: 'ada@example.com', created_at: '2025-01-01T00:00:00' }

/** Mock the API per path: /auth/me, /tasks, /tags. */
function mockApi(me: unknown, tasks: unknown = [], tags: unknown = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      let status = 200
      let body: unknown = null
      if (url.includes('/auth/me')) {
        if (me === null) {
          status = 401
        } else {
          body = me
        }
      } else if (url.includes('/tasks')) {
        body = tasks
      } else if (url.includes('/tags')) {
        body = tags
      }
      return new Response(body === null ? null : JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
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
    mockApi(null)
    const wrapper = await mountApp('/tasks')
    expect(wrapper.text()).toContain('Log in to your account')
  })

  it('shows the tasks view when authenticated', async () => {
    mockApi(USER)
    const wrapper = await mountApp('/tasks')
    const text = wrapper.text()
    expect(text).toContain('Tasks')
    expect(text).toContain('No tasks yet')
    expect(text).toContain('Calendar')
    expect(text).toContain('Session')
  })

  it('shows the calendar placeholder', async () => {
    mockApi(USER)
    const wrapper = await mountApp('/calendar')
    expect(wrapper.text()).toContain('Timeboxes land in M3')
  })

  it('sends authenticated users away from /login', async () => {
    mockApi(USER)
    const wrapper = await mountApp('/login')
    expect(wrapper.text()).toContain('No tasks yet')
  })
})
