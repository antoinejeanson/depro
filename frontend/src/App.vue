<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { RouterLink, RouterView } from 'vue-router'

import CalendarIcon from './components/icons/CalendarIcon.vue'
import DownloadIcon from './components/icons/DownloadIcon.vue'
import LogOutIcon from './components/icons/LogOutIcon.vue'
import PlayIcon from './components/icons/PlayIcon.vue'
import TasksIcon from './components/icons/TasksIcon.vue'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const auth = useAuthStore()

// Public routes (login/register) render full-screen, outside the app shell.
const isPublic = computed(() => route.meta.public === true)

const tabs = [
  { to: '/tasks', label: 'Tasks', icon: TasksIcon },
  { to: '/calendar', label: 'Calendar', icon: CalendarIcon },
  { to: '/session', label: 'Session', icon: PlayIcon },
]

const isActive = (to: string) => route.path === to

const exporting = ref(false)

// Download the user's data as a JSON file (tasks, tags, timeboxes, series).
async function exportData() {
  if (exporting.value) return
  exporting.value = true
  try {
    const res = await fetch('/api/export', { credentials: 'same-origin' })
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `depro-export-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

async function logout() {
  await auth.logout()
}
</script>

<template>
  <RouterView v-if="isPublic" />

  <template v-else>
    <!-- Desktop: left sidebar -->
    <aside
      class="fixed inset-y-0 left-0 z-10 hidden w-52 flex-col border-r border-gray-200 bg-white p-4 md:flex"
    >
      <div class="px-2 pb-6 text-xl font-bold text-indigo-600">depro</div>
      <nav class="flex flex-col gap-1">
        <RouterLink
          v-for="t in tabs"
          :key="t.to"
          :to="t.to"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
          :class="
            isActive(t.to)
              ? 'bg-indigo-50 text-indigo-700'
              : 'text-gray-600 hover:bg-gray-100'
          "
        >
          <component :is="t.icon" />
          {{ t.label }}
        </RouterLink>
      </nav>
      <div class="mt-auto flex flex-col gap-1">
        <button
          type="button"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          @click="exportData"
        >
          <DownloadIcon />
          Export data
        </button>
        <button
          type="button"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          @click="logout"
        >
          <LogOutIcon />
          Log out
        </button>
      </div>
    </aside>

    <!-- Mobile: top bar -->
    <header
      class="fixed inset-x-0 top-0 z-10 flex h-12 items-center justify-between border-b border-gray-200 bg-white px-4 md:hidden"
    >
      <span class="text-lg font-bold text-indigo-600">depro</span>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Export data"
          @click="exportData"
        >
          <DownloadIcon />
        </button>
        <button
          type="button"
          class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Log out"
          @click="logout"
        >
          <LogOutIcon />
        </button>
      </div>
    </header>

    <main class="min-h-screen pb-16 pt-12 md:pb-0 md:pl-52 md:pt-0">
      <div class="mx-auto max-w-3xl p-4 md:p-8">
        <RouterView />
      </div>
    </main>

    <!-- Mobile: bottom tab bar -->
    <nav
      class="fixed inset-x-0 bottom-0 z-10 grid h-16 grid-cols-3 border-t border-gray-200 bg-white md:hidden"
    >
      <RouterLink
        v-for="t in tabs"
        :key="t.to"
        :to="t.to"
        class="flex flex-col items-center justify-center gap-0.5 text-xs font-medium"
        :class="isActive(t.to) ? 'text-indigo-600' : 'text-gray-500'"
      >
        <component :is="t.icon" />
        {{ t.label }}
      </RouterLink>
    </nav>
  </template>
</template>
