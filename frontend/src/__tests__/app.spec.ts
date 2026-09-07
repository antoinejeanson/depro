import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '../App.vue'
import { setupAuthGuard } from '../auth/guard'
import { routes } from '../router'

const USER = { id: '1', email: 'ada@example.com', created_at: '2025-01-01T00:00:00' }

/** Mock the API per path: /auth/me, /tasks, /tags, /timeboxes, /timebox-series. */
function mockApi(
  me: unknown,
  tasks: unknown = [],
  tags: unknown = [],
  timeboxes: unknown = [],
  series: unknown = [],
) {
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
      } else if (url.includes('/timebox-series')) {
        body = series
      } else if (url.includes('/timeboxes')) {
        body = timeboxes
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

  it('shows the calendar with month grid and series section', async () => {
    mockApi(USER)
    const wrapper = await mountApp('/calendar')
    const text = wrapper.text()
    expect(text).toContain('Calendar')
    expect(text).toContain('Series')
    expect(text).toContain('Mon')
    expect(text).toContain('New series')
  })

  it('sends authenticated users away from /login', async () => {
    mockApi(USER)
    const wrapper = await mountApp('/login')
    expect(wrapper.text()).toContain('No tasks yet')
  })

  it('downloads the JSON export when Export data is clicked', async () => {
    mockApi(USER)
    const createObjectURL = vi.fn(() => 'blob:mock')
    const revokeObjectURL = vi.fn()
    const origCreate = URL.createObjectURL
    const origRevoke = URL.revokeObjectURL
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = revokeObjectURL
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    try {
      const wrapper = await mountApp('/tasks')
      const exportBtn = wrapper.find('button[aria-label="Export data"]')
      expect(exportBtn.exists()).toBe(true)
      await exportBtn.trigger('click')
      await flushPromises()

      const fetchMock = vi.mocked(fetch)
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes('/api/export')),
      ).toBe(true)
      expect(createObjectURL).toHaveBeenCalled()
      expect(clickSpy).toHaveBeenCalled()
    } finally {
      clickSpy.mockRestore()
      URL.createObjectURL = origCreate
      URL.revokeObjectURL = origRevoke
    }
  })
})
