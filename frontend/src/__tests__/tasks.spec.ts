import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TaskEditor from '../components/TaskEditor.vue'
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
  recurrence: null,
  next_due_at: null,
  parents: [],
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

  it('shows a waiting badge while a parent is open', () => {
    const wrapper = mount(TaskItem, {
      props: {
        task: {
          ...BASE_TASK,
          parents: [{ id: 'p1', title: 'Plan the trip', status: 'todo' }],
        },
      },
    })
    expect(wrapper.text()).toContain('waiting')
    expect(wrapper.find('[title]').attributes('title')).toContain('Plan the trip')
  })

  it('hides the waiting badge when all parents are done', () => {
    const wrapper = mount(TaskItem, {
      props: {
        task: {
          ...BASE_TASK,
          parents: [{ id: 'p1', title: 'Plan the trip', status: 'done' }],
        },
      },
    })
    expect(wrapper.text()).not.toContain('waiting')
  })

  it('shows the recurrence label and the next occurrence as the due date', () => {
    const wrapper = mount(TaskItem, {
      props: {
        task: {
          ...BASE_TASK,
          due_at: '2026-01-05T09:00:00', // anchor, in the past
          recurrence: {
            frequency: 'weekly',
            interval: 1,
            weekdays: [0],
            day_of_month: null,
          },
          next_due_at: '2026-09-14T09:00:00',
        },
      },
    })
    const text = wrapper.text()
    expect(text).toContain('weekly')
    // The pending occurrence, not the anchor, is shown.
    expect(text).toContain('Sep 14')
    expect(text).not.toContain('Jan 5')
  })
})

describe('TaskEditor', () => {
  const json = { 'Content-Type': 'application/json' }

  function makeTask(overrides: Partial<Task> = {}): Task {
    return {
      id: 't1',
      title: 'Task',
      notes: null,
      priority: null,
      due_at: null,
      status: 'todo',
      progress: 0,
      estimated_minutes: null,
      recurrence: null,
      next_due_at: null,
      parents: [],
      tags: [],
      created_at: '2026-09-01T00:00:00',
      updated_at: '2026-09-01T00:00:00',
      completed_at: null,
      ...overrides,
    }
  }

  function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), { status, headers: json })
  }

  it('sends recurrence and parents in the payload', async () => {
    setActivePinia(createPinia())
    const parent = makeTask({ id: 'p1', title: 'Parent task' })
    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(jsonResponse([parent])) // GET /tasks (picker)
      .mockResolvedValueOnce(jsonResponse(makeTask(), 201)) // POST /tasks
      .mockResolvedValueOnce(jsonResponse([makeTask()])) // fetchTasks
      .mockResolvedValueOnce(jsonResponse([])) // fetchTags
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(TaskEditor, { props: { task: null } })
    await flushPromises()

    await wrapper
      .find('input[placeholder="What needs to be done?"]')
      .setValue('Water plants')
    await wrapper.find('input[type="datetime-local"]').setValue('2026-09-15T09:00')

    // Turn on recurrence, switch to weekly.
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('select[aria-label="Recurrence frequency"]').setValue('weekly')

    // Add the parent from the picker.
    await wrapper.find('select[aria-label="Add parent"]').setValue('p1')

    // Save.
    const save = wrapper.findAll('button').find((b) => b.text() === 'Save')!
    await save.trigger('click')
    await flushPromises()

    const post = fetchMock.mock.calls.find((c) => c[1]?.method === 'POST')
    const body = JSON.parse(post![1].body as string)
    expect(body.title).toBe('Water plants')
    expect(body.recurrence).toEqual({
      frequency: 'weekly',
      interval: 1,
      weekdays: [0],
      day_of_month: null,
    })
    expect(body.parents).toEqual(['p1'])
  })

  it('refuses to save a recurring task without a due date', async () => {
    setActivePinia(createPinia())
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(TaskEditor, { props: { task: null } })
    await flushPromises()

    await wrapper
      .find('input[placeholder="What needs to be done?"]')
      .setValue('Water plants')
    await wrapper.find('input[type="checkbox"]').setValue(true)

    const save = wrapper.findAll('button').find((b) => b.text() === 'Save')!
    await save.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('due date')
    expect(fetchMock.mock.calls.find((c) => c[1]?.method === 'POST')).toBeUndefined()
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
      recurrence: null,
      parents: [],
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
