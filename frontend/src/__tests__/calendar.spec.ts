import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MonthGrid from '../components/MonthGrid.vue'
import { useTimeboxesStore, type Timebox } from '../stores/timeboxes'
import { describeRule, monthCells, type DayCell } from '../utils/calendar'

const TB: Timebox = {
  id: '1',
  title: 'Focus',
  starts_at: '2026-09-07T09:00:00',
  ends_at: '2026-09-07T11:00:00',
  series_id: null,
  series_title: null,
}

describe('describeRule', () => {
  it('describes daily rules', () => {
    expect(
      describeRule({ frequency: 'daily', interval: 1, weekdays: [], day_of_month: null, start_time: '09:00', end_time: '10:00' }),
    ).toBe('Daily · 09:00–10:00')
    expect(
      describeRule({ frequency: 'daily', interval: 2, weekdays: [], day_of_month: null, start_time: '09:00', end_time: '10:00' }),
    ).toBe('Every 2 days · 09:00–10:00')
  })

  it('describes weekly rules', () => {
    expect(
      describeRule({ frequency: 'weekly', interval: 1, weekdays: [2, 0], day_of_month: null, start_time: '19:00', end_time: '21:00' }),
    ).toBe('Mon, Wed · 19:00–21:00')
    expect(
      describeRule({ frequency: 'weekly', interval: 2, weekdays: [0], day_of_month: null, start_time: '19:00', end_time: '21:00' }),
    ).toBe('Every 2 weeks on Mon · 19:00–21:00')
  })

  it('describes monthly rules', () => {
    expect(
      describeRule({ frequency: 'monthly', interval: 1, weekdays: [], day_of_month: 15, start_time: '08:00', end_time: '09:00' }),
    ).toBe('day 15 · 08:00–09:00')
  })
})

describe('monthCells', () => {
  it('produces 42 Monday-first cells covering the month', () => {
    // September 2026: the 1st is a Tuesday, so the grid starts Mon Aug 31.
    const cells = monthCells(2026, 8, [])
    expect(cells).toHaveLength(42)
    expect(cells[0].date).toBe('2026-08-31')
    expect(cells[0].inMonth).toBe(false)
    expect(cells[1].date).toBe('2026-09-01')
    expect(cells[1].inMonth).toBe(true)
    const seps = cells.filter((c) => c.inMonth)
    expect(seps).toHaveLength(30)
  })

  it('groups timeboxes by start day', () => {
    const cells = monthCells(2026, 8, [TB])
    const sep7 = cells.find((c) => c.date === '2026-09-07')
    expect(sep7?.timeboxes).toEqual([TB])
    const sep8 = cells.find((c) => c.date === '2026-09-08')
    expect(sep8?.timeboxes).toEqual([])
  })
})

function makeCells(): DayCell[] {
  // Grid for Sep 2026, Monday-first: starts Mon Aug 31.
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(2026, 7, 31 + i)
    const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return { date, inMonth: d.getMonth() === 8, isToday: date === '2026-09-07', timeboxes: [] }
  })
}

describe('MonthGrid', () => {
  it('renders 42 cells and weekday headers', () => {
    const wrapper = mount(MonthGrid, { props: { cells: makeCells() } })
    expect(wrapper.text()).toContain('Mon')
    expect(wrapper.text()).toContain('Sun')
    expect(wrapper.findAll('[class*="min-h-16"]')).toHaveLength(42)
  })

  it('emits day-click when a cell is clicked', async () => {
    const wrapper = mount(MonthGrid, { props: { cells: makeCells() } })
    await wrapper.findAll('[class*="min-h-16"]')[1].trigger('click')
    expect(wrapper.emitted('day-click')?.[0]).toEqual(['2026-09-01'])
  })

  it('emits timebox-click (not day-click) when a chip is clicked', async () => {
    const cells = makeCells()
    const sep7 = cells.find((c) => c.date === '2026-09-07')!
    sep7.timeboxes = [TB]
    const wrapper = mount(MonthGrid, { props: { cells } })
    await wrapper.find('button.bg-teal-100').trigger('click')
    expect(wrapper.emitted('timebox-click')?.[0]).toEqual([TB])
    expect(wrapper.emitted('day-click')).toBeUndefined()
  })

  it('shows a "+N more" overflow link', () => {
    const cells = makeCells()
    const sep7 = cells.find((c) => c.date === '2026-09-07')!
    sep7.timeboxes = [1, 2, 3, 4].map((n) => ({ ...TB, id: String(n) }))
    const wrapper = mount(MonthGrid, { props: { cells } })
    expect(wrapper.text()).toContain('+1 more')
  })
})

describe('timeboxes store', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function freshStore() {
    setActivePinia(createPinia())
    return useTimeboxesStore()
  }

  it('loadRange fetches the range and remembers it', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    await store.loadRange('2026-09-01', '2026-10-05')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/timeboxes?start=2026-09-01&end=2026-10-05')
    expect(store.range).toEqual({ start: '2026-09-01', end: '2026-10-05' })
  })

  it('createOneOff posts the payload', async () => {
    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify(TB), { status: 201, headers: { 'Content-Type': 'application/json' } }),
      )
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    store.range = { start: '2026-09-01', end: '2026-10-05' }
    await store.createOneOff({ title: 'Focus', starts_at: '2026-09-07T09:00:00', ends_at: '2026-09-07T11:00:00' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/timeboxes')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
  })

  it('deleteSeries hits the series endpoint', async () => {
    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
      .mockResolvedValueOnce(
        new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const store = freshStore()
    store.range = { start: '2026-09-01', end: '2026-10-05' }
    await store.deleteSeries('abc')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/timebox-series/abc')
    expect(fetchMock.mock.calls[0][1]?.method).toBe('DELETE')
  })
})
