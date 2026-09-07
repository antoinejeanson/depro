import { api } from '../api/client'
import { defineStore } from 'pinia'

export type TaskStatus = 'todo' | 'in_progress' | 'done'

export interface Task {
  id: string
  title: string
  notes: string | null
  priority: number | null
  due_at: string | null
  status: TaskStatus
  progress: number
  estimated_minutes: number | null
  tags: string[]
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface Tag {
  id: string
  name: string
  task_count: number
}

export interface TaskPayload {
  title: string
  notes: string | null
  priority: number | null
  due_at: string | null
  estimated_minutes: number | null
  tags: string[]
}

export interface TaskFilters {
  q: string
  status: TaskStatus | ''
  tag: string
}

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [] as Task[],
    tags: [] as Tag[],
    filters: { q: '', status: '', tag: '' } as TaskFilters,
    loading: false,
  }),
  actions: {
    async fetchTasks() {
      this.loading = true
      try {
        const params = new URLSearchParams()
        if (this.filters.q) params.set('q', this.filters.q)
        if (this.filters.status) params.set('status', this.filters.status)
        if (this.filters.tag) params.set('tag', this.filters.tag)
        const qs = params.toString()
        this.tasks = await api<Task[]>(`/tasks${qs ? `?${qs}` : ''}`)
      } finally {
        this.loading = false
      }
    },
    async fetchTags() {
      this.tags = await api<Tag[]>('/tags')
    },
    async createTask(payload: TaskPayload) {
      await api<Task>('/tasks', { method: 'POST', body: JSON.stringify(payload) })
      await Promise.all([this.fetchTasks(), this.fetchTags()])
    },
    async updateTask(id: string, payload: TaskPayload) {
      await api<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
      await Promise.all([this.fetchTasks(), this.fetchTags()])
    },
    async deleteTask(id: string) {
      await api<void>(`/tasks/${id}`, { method: 'DELETE' })
      await Promise.all([this.fetchTasks(), this.fetchTags()])
    },
    async setProgress(id: string, progress: number) {
      await api<Task>(`/tasks/${id}/progress`, {
        method: 'POST',
        body: JSON.stringify({ progress }),
      })
      await this.fetchTasks()
    },
    async completeTask(id: string) {
      await api<Task>(`/tasks/${id}/complete`, { method: 'POST' })
      await this.fetchTasks()
    },
  },
})
