import { api } from '../api/client'
import { defineStore } from 'pinia'

import type { Task } from './tasks'

export type Frequency = 'daily' | 'weekly' | 'monthly'

export interface SeriesRule {
  frequency: Frequency
  interval: number
  weekdays: number[] // 0 = Monday .. 6 = Sunday
  day_of_month: number | null
  start_time: string // "HH:MM"
  end_time: string
}

export interface Series {
  id: string
  title: string
  rule: SeriesRule
  active: boolean
  start_date: string
  created_at: string
}

export interface Timebox {
  id: string
  title: string | null
  starts_at: string
  ends_at: string
  series_id: string | null
  series_title: string | null
}

export interface OneOffPayload {
  title: string | null
  starts_at: string
  ends_at: string
}

export interface PlanEntry {
  task: Task
  tier: number // 1-4
  reason: string
}

export interface PlanResponse {
  timebox: Timebox
  state: 'upcoming' | 'active' | 'past'
  plan: PlanEntry[]
  completed: Task[] // tasks completed during the window (past boxes)
}

interface Range {
  start: string
  end: string
}

export const useTimeboxesStore = defineStore('timeboxes', {
  state: () => ({
    timeboxes: [] as Timebox[],
    series: [] as Series[],
    range: null as Range | null,
    loading: false,
  }),
  actions: {
    async loadRange(start: string, end: string) {
      this.range = { start, end }
      this.loading = true
      try {
        this.timeboxes = await api<Timebox[]>(`/timeboxes?start=${start}&end=${end}`)
      } finally {
        this.loading = false
      }
    },
    async fetchSeries() {
      this.series = await api<Series[]>('/timebox-series')
    },
    async refresh() {
      if (!this.range) return
      await Promise.all([
        this.loadRange(this.range.start, this.range.end),
        this.fetchSeries(),
      ])
    },
    async createOneOff(payload: OneOffPayload) {
      await api<Timebox>('/timeboxes', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      await this.refresh()
    },
    async deleteOneOff(id: string) {
      await api<void>(`/timeboxes/${id}`, { method: 'DELETE' })
      await this.refresh()
    },
    async createSeries(payload: { title: string; rule: SeriesRule }) {
      await api<Series>('/timebox-series', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      await this.refresh()
    },
    async updateSeries(
      id: string,
      payload: { title: string; rule: SeriesRule; active: boolean },
    ) {
      await api<Series>(`/timebox-series/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      await this.refresh()
    },
    async deleteSeries(id: string) {
      await api<void>(`/timebox-series/${id}`, { method: 'DELETE' })
      await this.refresh()
    },
    async fetchPlan(id: string) {
      return api<PlanResponse>(`/timeboxes/${id}/plan`)
    },
  },
})
