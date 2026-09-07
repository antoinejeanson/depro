import { api } from '../api/client'
import { defineStore } from 'pinia'

import type { PlanEntry, Timebox } from './timeboxes'

export interface NowState {
  timebox: Timebox | null
  state: 'active' | 'idle'
  plan: PlanEntry[]
  current: PlanEntry | null
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    now: null as NowState | null,
    loading: false,
  }),
  actions: {
    async fetchNow() {
      this.loading = true
      try {
        this.now = await api<NowState>('/timeboxes/now')
      } finally {
        this.loading = false
      }
    },
    async startSpontaneous(minutes: number) {
      await api<Timebox>('/timeboxes/spontaneous', {
        method: 'POST',
        body: JSON.stringify({ minutes }),
      })
      await this.fetchNow()
    },
  },
})
