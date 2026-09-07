import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import PlanList from '../components/PlanList.vue'
import { routes } from '../router'
import { useSessionStore } from '../stores/session'
import type { Task } from '../stores/tasks'
import type { PlanEntry } from '../stores/timeboxes'
import SessionView from '../views/SessionView.vue'

const TASK: Task = {
  id: 't1',
  title: 'Overdue report',
  notes: null,
  priority: 7,
  due_at: '2026-09-05T17:00:00',
  status: 'todo',
  progress: 0,
  estimated_minutes: 45,
  recurrence: null,
  next_due_at: null,
  parents: [],
  tags: [],
  created_at: '2026-09-01T00:00:00',
  updated_at: '2026-09-01T00:00:00',
  completed_at: null,
}

const ENTRY: PlanEntry = { task: TASK, tier: 1, reason: 'Overdue (due Sep 05)' }

const NOW_BODY = {
  timebox: {
    id: 'b1',
    title: 'Focus',
    starts_at: '2026-09-07T17:00:00',
    ends_at: '2026-09-07T19:00:00',
    series_id: null,
    series_title: null,
  },
  state: 'active',
  plan: [ENTRY],
  current: ENTRY,
}

const IDLE_BODY = { timebox: null, state: 'idle', plan: [], current: null }

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const body = handler(String(input), init)
    return new Response(body === null ? null : JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function mountSession() {
  setActivePinia(createPinia())
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push('/session')
  await router.isReady()
  const wrapper = mount(SessionView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('PlanList', () => {
  it('renders entries with tier label, title, reason and estimate', () => {
    const wrapper = mount(PlanList, { props: { entries: [ENTRY] } })
    const text = wrapper.text()
    expect(text).toContain('Urgent')
    expect(text).toContain('Overdue report')
    expect(text).toContain('Overdue (due Sep 05)')
    expect(text).toContain('45m')
  })

  it('labels all four tiers', () => {
    const entries = [1, 2, 3, 4].map((tier) => ({ ...ENTRY, tier }))
    const wrapper = mount(PlanList, { props: { entries } })
    const text = wrapper.text()
    expect(text).toContain('Urgent')
    expect(text).toContain('In progress')
    expect(text).toContain('Fits')
    expect(text).toContain("Doesn't fit")
  })
})

describe('session store', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetchNow stores the /now payload', async () => {
    mockFetch((url) => (url.includes('/timeboxes/now') ? NOW_BODY : []))
    setActivePinia(createPinia())
    const store = useSessionStore()
    await store.fetchNow()
    expect(store.now?.state).toBe('active')
    expect(store.now?.current?.task.title).toBe('Overdue report')
  })

  it('startSpontaneous posts the minutes and refetches', async () => {
    const calls: string[] = []
    mockFetch((url, init) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.includes('/timeboxes/spontaneous')) return NOW_BODY.timebox
      if (url.includes('/timeboxes/now')) return NOW_BODY
      return []
    })
    setActivePinia(createPinia())
    const store = useSessionStore()
    await store.startSpontaneous(45)
    expect(calls[0]).toBe('POST /api/timeboxes/spontaneous')
    expect(calls.some((c) => c.startsWith('GET /api/timeboxes/now'))).toBe(true)
    expect(store.now?.state).toBe('active')
  })
})

describe('SessionView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the idle state with a spontaneous start', async () => {
    mockFetch((url) => (url.includes('/timeboxes/now') ? IDLE_BODY : []))
    const wrapper = await mountSession()
    const text = wrapper.text()
    expect(text).toContain('No active timebox')
    expect(text).toContain('Start a spontaneous session')
    expect(text).toContain('60 min')
    expect(text).toContain('Start now')
    wrapper.unmount()
  })

  it('shows the current task and queue when active', async () => {
    const queueEntry: PlanEntry = {
      task: { ...TASK, id: 't2', title: 'Quick email', progress: 0 },
      tier: 3,
      reason: 'Priority 9, fits in 15 min',
    }
    const body = { ...NOW_BODY, plan: [ENTRY, queueEntry] }
    mockFetch((url) => (url.includes('/timeboxes/now') ? body : []))
    const wrapper = await mountSession()
    const text = wrapper.text()
    expect(text).toContain('Do this now')
    expect(text).toContain('Overdue report')
    expect(text).toContain('Overdue (due Sep 05)')
    expect(text).toContain('Up next in this timebox')
    expect(text).toContain('Quick email')
    wrapper.unmount()
  })

  it('completing the current task calls the complete endpoint', async () => {
    const calls: string[] = []
    mockFetch((url, init) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.includes('/timeboxes/now')) return NOW_BODY
      if (url.includes('/tasks')) return []
      return []
    })
    const wrapper = await mountSession()
    await wrapper.find('button.bg-emerald-600').trigger('click')
    await flushPromises()
    expect(calls.some((c) => c === 'POST /api/tasks/t1/complete')).toBe(true)
    wrapper.unmount()
  })

  it('bumping progress posts the new value', async () => {
    const calls: string[] = []
    mockFetch((url, init) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.includes('/timeboxes/now')) return NOW_BODY
      return []
    })
    const wrapper = await mountSession()
    await wrapper.find('button.border-gray-300').trigger('click')
    await flushPromises()
    const progressCall = calls.find((c) => c.startsWith('POST /api/tasks/t1/progress'))
    expect(progressCall).toBeDefined()
    wrapper.unmount()
  })
})
