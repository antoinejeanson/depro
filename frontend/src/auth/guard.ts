import type { Router } from 'vue-router'

import { useAuthStore } from '../stores/auth'

/**
 * Route guard: unauthenticated users are sent to /login (with a redirect
 * back to the intended page); authenticated users skip /login and /register.
 *
 * Must be called after the pinia instance is installed on the app.
 */
export function setupAuthGuard(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (!auth.checked) {
      await auth.fetchMe()
    }
    const isPublic = to.meta.public === true
    if (!auth.user && !isPublic) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (auth.user && isPublic) {
      return { path: '/tasks' }
    }
  })
}
