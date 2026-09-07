import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TaskItem from '../components/TaskItem.vue'
import { useTasksStore, type Task } from '../stores/tasks'

const BASE_TASK: Task = {
  id: '1',
  title: 'Buy groceries',
  notes: null,
  priority: 7,
  due_at: null,
  status: 'todo',
  progress: 0,
  estimated_minutes: 30,
  tags: ['errands'],
  created_at: '2026-09-01T00:00:00',
  updated_at: '2026-09-01T00:00:00',
  completed_at: null,
}

describe('TaskItem', () => {
  it('renders title, priority, estimate and tags', () => {
    const wrapper = mount(TaskItem, { props: { task: BASE_TASK } })
    const text = wrapper.text()
    expect(text).toContain('Buy groceries')
    expect(text).toContain('P7')
    expect(text).toContain('30 min')
    expect(text).toContain('#errands')
  })

  it('strikethroughs done tasks', () => {
    const wrapper = mount(TaskItem, {
      props: { task: { ...BASE_TASK, status: 'done', progress: 100 } },
    })
    expect(wrapper.find('.line-through').exists()).toBe(true)
  })

  it('shows the progress number for in-progress tasks', () => {
    const wrapper = mount(TaskItem, {
      props: { task: { ...BASE_TASK, status: 'in_progress', progress: 40 } },
    })
    expect(wrapper.text()).toContain('40')
  })
})

describe('tasks store', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function freshStore() {
    setActivePinia(createPinia())
    return useTasksStore()
  }

  it('fetchTasks sends filters as query params', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    store.filters.q = 'buy'
    store.filters.status = 'todo'
    await store.fetchTasks()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/tasks?q=buy&status=todo')
  })

  it('createTask posts the payload', async () => {
    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(BASE_TASK), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify([BASE_TASK]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    await store.createTask({
      title: 'Buy groceries',
      notes: null,
      priority: null,
      due_at: null,
      estimated_minutes: null,
      tags: [],
    })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/tasks')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(store.tasks).toHaveLength(1)
  })

  it('setProgress posts to the progress endpoint', async () => {
    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ...BASE_TASK, progress: 50 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    await store.setProgress('1', 50)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/tasks/1/progress')
    const body = JSON.parse(fetchMock.mock.calls[0][1]?.body as string)
    expect(body).toEqual({ progress: 50 })
  })
})
