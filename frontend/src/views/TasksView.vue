<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import TaskEditor from '../components/TaskEditor.vue'
import TaskItem from '../components/TaskItem.vue'
import { useTasksStore, type Task } from '../stores/tasks'

const store = useTasksStore()
const editorOpen = ref(false)
const editingTask = ref<Task | null>(null)

onMounted(() => {
  store.fetchTasks()
  store.fetchTags()
})

// Debounce the search box; status/tag changes apply immediately.
let searchTimer: number | undefined
watch(
  () => store.filters.q,
  () => {
    window.clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => store.fetchTasks(), 250)
  },
)
watch(
  () => [store.filters.status, store.filters.tag],
  () => store.fetchTasks(),
)

function openNew() {
  editingTask.value = null
  editorOpen.value = true
}

function openEdit(task: Task) {
  editingTask.value = task
  editorOpen.value = true
}

const hasActiveFilters = () =>
  Boolean(store.filters.q || store.filters.status || store.filters.tag)
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">Tasks</h1>
      <button
        type="button"
        class="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        @click="openNew"
      >
        + New task
      </button>
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <input
        v-model="store.filters.q"
        type="search"
        placeholder="Search…"
        class="min-w-40 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />
      <select
        v-model="store.filters.status"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      >
        <option value="">All statuses</option>
        <option value="todo">To-do</option>
        <option value="in_progress">In progress</option>
        <option value="done">Done</option>
      </select>
      <select
        v-model="store.filters.tag"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      >
        <option value="">All tags</option>
        <option v-for="t in store.tags" :key="t.id" :value="t.name">
          {{ t.name }} ({{ t.task_count }})
        </option>
      </select>
    </div>

    <ul
      v-if="store.tasks.length"
      class="mt-4 divide-y divide-gray-200 rounded-xl border border-gray-200 bg-white"
    >
      <li v-for="task in store.tasks" :key="task.id">
        <TaskItem :task="task" @edit="openEdit(task)" />
      </li>
    </ul>
    <p v-else class="mt-10 text-center text-sm text-gray-500">
      {{
        hasActiveFilters()
          ? 'No tasks match the filters.'
          : 'No tasks yet — add your first one.'
      }}
    </p>

    <TaskEditor
      v-if="editorOpen"
      :task="editingTask"
      @close="editorOpen = false"
    />
  </div>
</template>
