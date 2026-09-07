<script setup lang="ts">
import { computed } from 'vue'
import dayjs from 'dayjs'

import type { Task } from '../stores/tasks'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{ edit: [] }>()

const now = dayjs()

const isDone = computed(() => props.task.status === 'done')
const overdue = computed(
  () =>
    props.task.due_at !== null &&
    !isDone.value &&
    dayjs(props.task.due_at).isBefore(now, 'minute'),
)
const dueToday = computed(
  () => props.task.due_at !== null && dayjs(props.task.due_at).isSame(now, 'day'),
)

const priorityClass = computed(() => {
  const p = props.task.priority
  if (p === null) return ''
  if (p >= 7) return 'bg-red-100 text-red-700'
  if (p >= 4) return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-600'
})

const dueClass = computed(() => {
  if (overdue.value) return 'bg-red-100 text-red-700 font-semibold'
  if (dueToday.value) return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-500'
})

const dueLabel = computed(() => {
  if (props.task.due_at === null) return ''
  const due = dayjs(props.task.due_at)
  return `${overdue.value ? 'Overdue — ' : ''}${due.format('MMM D, HH:mm')}`
})
</script>

<template>
  <button
    type="button"
    class="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50"
    @click="emit('edit')"
  >
    <!-- Status indicator -->
    <span
      v-if="isDone"
      class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-500 text-[10px] font-bold text-white"
    >
      ✓
    </span>
    <span
      v-else-if="task.status === 'in_progress'"
      class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-indigo-500 text-[9px] font-bold text-indigo-600"
    >
      {{ task.progress }}
    </span>
    <span v-else class="h-5 w-5 shrink-0 rounded-full border-2 border-gray-300" />

    <span class="min-w-0 flex-1">
      <span
        class="block truncate text-sm font-medium"
        :class="isDone ? 'text-gray-400 line-through' : 'text-gray-900'"
      >
        {{ task.title }}
      </span>
      <span class="mt-0.5 flex flex-wrap gap-1">
        <span
          v-if="task.priority !== null"
          class="rounded px-1.5 py-0.5 text-[11px] font-semibold"
          :class="priorityClass"
        >
          P{{ task.priority }}
        </span>
        <span
          v-if="task.due_at !== null"
          class="rounded px-1.5 py-0.5 text-[11px]"
          :class="dueClass"
        >
          {{ dueLabel }}
        </span>
        <span
          v-if="task.estimated_minutes !== null"
          class="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500"
        >
          {{ task.estimated_minutes }} min
        </span>
        <span
          v-for="tag in task.tags"
          :key="tag"
          class="rounded bg-indigo-50 px-1.5 py-0.5 text-[11px] text-indigo-600"
        >
          #{{ tag }}
        </span>
      </span>
    </span>
  </button>
</template>
