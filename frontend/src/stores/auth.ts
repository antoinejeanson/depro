import { api } from '../api/client'
import { defineStore } from 'pinia'

export interface User {
  id: string
  email: string
  created_at: string
}

interface AuthState {
  user: User | null
  /** True once the session has been checked at least once this page load. */
  checked: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({ user: null, checked: false }),
  actions: {
    async fetchMe() {
      try {
        this.user = await api<User>('/auth/me')
      } catch {
        this.user = null
      } finally {
        this.checked = true
      }
    },
    async login(email: string, password: string) {
      this.user = await api<User>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      this.checked = true
    },
    async register(email: string, password: string) {
      this.user = await api<User>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      this.checked = true
    },
    async logout() {
      try {
        await api<void>('/auth/logout', { method: 'POST' })
      } catch {
        // Session may already be gone; log out locally either way.
      }
      this.user = null
    },
  },
})
