<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'

import { api } from '../api/client'
import {
  useTasksStore,
  type RecurrenceFrequency,
  type Task,
  type TaskParent,
  type TaskPayload,
} from '../stores/tasks'

const props = defineProps<{ task: Task | null }>()
const emit = defineEmits<{ close: [] }>()

const store = useTasksStore()
const saving = ref(false)
const deleting = ref(false)
const error = ref('')

const form = reactive({
  title: props.task?.title ?? '',
  notes: props.task?.notes ?? '',
  priority: props.task?.priority ?? null,
  // datetime-local value (local wall time), '' = no due date
  due_at: props.task?.due_at ? dayjs(props.task.due_at).format('YYYY-MM-DDTHH:mm') : '',
  // Bound as a string: number inputs yield '' when cleared, which is not a number.
  estimated_minutes:
    props.task && props.task.estimated_minutes !== null
      ? String(props.task.estimated_minutes)
      : '',
  tags: [...(props.task?.tags ?? [])],
  progress: props.task?.progress ?? 0,
  // Recurrence
  repeats: props.task?.recurrence !== null,
  recurrence_frequency: (props.task?.recurrence?.frequency ?? 'daily') as RecurrenceFrequency,
  recurrence_interval: String(props.task?.recurrence?.interval ?? 1),
  recurrence_weekdays: [...(props.task?.recurrence?.weekdays ?? [0])],
  recurrence_day_of_month: String(props.task?.recurrence?.day_of_month ?? 1),
  // Precedence
  parentIds: (props.task?.parents ?? []).map((p) => p.id),
})
const newTag = ref('')

// Parent picker: full (unfiltered) task list, excluding the task itself.
const allTasks = ref<Task[]>([])
onMounted(async () => {
  try {
    allTasks.value = await api<Task[]>('/tasks')
  } catch {
    // Picker stays empty; the task can still be saved without parents.
  }
})
const parentCandidates = computed(() =>
  allTasks.value
    .filter((t) => t.id !== props.task?.id)
    .sort((a, b) => a.title.localeCompare(b.title)),
)
const selectedParents = computed(() =>
  form.parentIds
    .map((id) => {
      const full = allTasks.value.find((t) => t.id === id)
      if (full) return full
      const known = props.task?.parents.find((p) => p.id === id)
      return known ? (known as TaskParent) : null
    })
    .filter((t): t is Task | TaskParent => t !== null),
)

function toggleWeekday(day: number) {
  const i = form.recurrence_weekdays.indexOf(day)
  if (i === -1) form.recurrence_weekdays.push(day)
  else form.recurrence_weekdays.splice(i, 1)
}

function addParent(event: Event) {
  const id = (event.target as HTMLSelectElement).value
  if (id && !form.parentIds.includes(id)) form.parentIds.push(id)
}

function removeParent(id: string) {
  form.parentIds = form.parentIds.filter((x) => x !== id)
}

function addTag() {
  const name = newTag.value.trim()
  if (name && !form.tags.some((t) => t.toLowerCase() === name.toLowerCase())) {
    form.tags.push(name)
  }
  newTag.value = ''
}

function removeTag(index: number) {
  form.tags.splice(index, 1)
}

function recurrencePayload() {
  if (!form.repeats) return null
  const frequency = form.recurrence_frequency
  return {
    frequency,
    interval: Math.max(1, Number(form.recurrence_interval) || 1),
    weekdays:
      frequency === 'weekly'
        ? [...form.recurrence_weekdays].sort((a, b) => a - b)
        : [],
    day_of_month:
      frequency === 'monthly' ? Number(form.recurrence_day_of_month) || null : null,
  }
}

function payload(): TaskPayload {
  return {
    title: form.title.trim(),
    notes: form.notes.trim() || null,
    priority: form.priority,
    // Naive local ISO — matches the backend's naive-local datetime design.
    due_at: form.due_at ? dayjs(form.due_at).format('YYYY-MM-DDTHH:mm:ss') : null,
    estimated_minutes:
      form.estimated_minutes === '' ? null : Number(form.estimated_minutes),
    recurrence: recurrencePayload(),
    parents: [...form.parentIds],
    tags: form.tags,
  }
}

async function save() {
  if (!form.title.trim()) {
    error.value = 'A title is required'
    return
  }
  if (form.repeats) {
    if (!form.due_at) {
      error.value = 'Recurring tasks need a due date — it anchors the schedule.'
      return
    }
    if (form.recurrence_frequency === 'weekly' && form.recurrence_weekdays.length === 0) {
      error.value = 'Pick at least one weekday for a weekly task.'
      return
    }
    const dom = Number(form.recurrence_day_of_month)
    if (
      form.recurrence_frequency === 'monthly' &&
      (!Number.isInteger(dom) || dom < 1 || dom > 31)
    ) {
      error.value = 'Day of month must be between 1 and 31.'
      return
    }
  }
  saving.value = true
  error.value = ''
  try {
    if (props.task) {
      await store.updateTask(props.task.id, payload())
      if (form.progress !== props.task.progress) {
        await store.setProgress(props.task.id, form.progress)
      }
    } else {
      await store.createTask(payload())
    }
    emit('close')
  } catch {
    error.value = 'Could not save the task. Please try again.'
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.task || !deleting.value) {
    deleting.value = true
    return
  }
  deleting.value = false
  saving.value = true
  try {
    await store.deleteTask(props.task.id)
    emit('close')
  } catch {
    error.value = 'Could not delete the task. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
    @click.self="emit('close')"
  >
    <div
      class="flex max-h-full w-full flex-col overflow-y-auto rounded-t-2xl bg-white p-4 shadow-xl sm:max-w-lg sm:rounded-2xl sm:p-6"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">
          {{ task ? 'Edit task' : 'New task' }}
        </h2>
        <button
          type="button"
          class="text-gray-400 hover:text-gray-600"
          aria-label="Close"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>

      <div class="mt-4 space-y-4">
        <input
          v-model="form.title"
          type="text"
          placeholder="What needs to be done?"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
        />
        <textarea
          v-model="form.notes"
          rows="3"
          placeholder="Notes (optional)"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
        />

        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">Priority</span>
            <select
              v-model.number="form.priority"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              <option :value="null">None</option>
              <option v-for="p in 10" :key="p" :value="p - 1">{{ p - 1 }}</option>
            </select>
          </label>
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">Estimated time (min)</span>
            <input
              v-model.number="form.estimated_minutes"
              type="number"
              min="1"
              placeholder="e.g. 30"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
        </div>

        <label class="block text-sm text-gray-700">
          <span class="mb-1 block">Due date</span>
          <input
            v-model="form.due_at"
            type="datetime-local"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </label>

        <!-- Recurrence -->
        <div class="rounded-lg border border-gray-200 p-3">
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input
              v-model="form.repeats"
              type="checkbox"
              class="h-4 w-4 accent-indigo-600"
            />
            <span class="font-medium">Repeats</span>
          </label>
          <div v-if="form.repeats" class="mt-3 space-y-3">
            <div class="flex flex-wrap items-center gap-2 text-sm text-gray-700">
              <span>Every</span>
              <input
                v-model="form.recurrence_interval"
                type="number"
                min="1"
                max="365"
                class="w-16 rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none"
              />
              <select
                v-model="form.recurrence_frequency"
                aria-label="Recurrence frequency"
                class="rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="daily">day(s)</option>
                <option value="weekly">week(s)</option>
                <option value="monthly">month(s)</option>
              </select>
            </div>
            <div
              v-if="form.recurrence_frequency === 'weekly'"
              class="flex flex-wrap gap-1"
            >
              <button
                v-for="(label, i) in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']"
                :key="label"
                type="button"
                class="rounded px-2 py-1 text-xs font-medium"
                :class="
                  form.recurrence_weekdays.includes(i)
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                "
                @click="toggleWeekday(i)"
              >
                {{ label }}
              </button>
            </div>
            <label
              v-if="form.recurrence_frequency === 'monthly'"
              class="flex items-center gap-2 text-sm text-gray-700"
            >
              <span>On day</span>
              <input
                v-model="form.recurrence_day_of_month"
                type="number"
                min="1"
                max="31"
                class="w-16 rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none"
              />
              <span>of the month</span>
            </label>
            <p class="text-xs text-gray-500">
              The due date anchors the schedule. Completing the task reschedules it
              for the next occurrence instead of finishing it.
            </p>
          </div>
        </div>

        <!-- Precedence -->
        <div>
          <span class="mb-1 block text-sm text-gray-700">Waits for (optional)</span>
          <p class="mb-2 text-xs text-gray-500">
            This task only enters plans once all of its parents are done.
          </p>
          <div class="flex flex-wrap items-center gap-1">
            <span
              v-for="p in selectedParents"
              :key="p.id"
              class="flex items-center gap-1 rounded bg-purple-50 px-2 py-0.5 text-xs text-purple-700"
            >
              {{ p.title }}
              <button
                type="button"
                class="hover:text-purple-900"
                aria-label="Remove parent"
                @click="removeParent(p.id)"
              >
                ✕
              </button>
            </span>
            <select
              v-if="parentCandidates.length"
              :value="''"
              class="rounded-lg border border-gray-300 px-2 py-1 text-xs focus:border-indigo-500 focus:outline-none"
              aria-label="Add parent"
              @change="addParent($event)"
            >
              <option value="">+ Add parent…</option>
              <option v-for="t in parentCandidates" :key="t.id" :value="t.id">
                {{ t.title }}
              </option>
            </select>
          </div>
        </div>

        <div>
          <span class="mb-1 block text-sm text-gray-700">Tags</span>
          <div
            class="flex flex-wrap items-center gap-1 rounded-lg border border-gray-300 px-2 py-1.5"
          >
            <template v-for="(tag, i) in form.tags" :key="tag">
              <span
                class="flex items-center gap-1 rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
              >
                #{{ tag }}
                <button
                  type="button"
                  class="hover:text-indigo-900"
                  aria-label="Remove tag"
                  @click="removeTag(i)"
                >
                  ✕
                </button>
              </span>
            </template>
            <input
              v-model="newTag"
              type="text"
              placeholder="Add tag…"
              class="min-w-24 flex-1 border-none px-1 py-0.5 text-sm focus:outline-none"
              @keydown.enter.prevent="addTag"
              @blur="addTag"
            />
          </div>
        </div>

        <!-- Progress: existing tasks only -->
        <div v-if="task" class="rounded-lg bg-gray-50 p-3">
          <div class="flex items-center justify-between text-sm text-gray-700">
            <span>
              Progress:
              <strong>{{ form.progress }}%</strong>
            </span>
            <span class="text-xs text-gray-500">
              {{
                form.progress === 0
                  ? 'To-do'
                  : form.progress === 100
                    ? 'Done'
                    : 'In progress'
              }}
            </span>
          </div>
          <input
            v-model.number="form.progress"
            type="range"
            min="0"
            max="100"
            step="5"
            class="mt-2 w-full accent-indigo-600"
          />
          <div class="mt-1 flex gap-2">
            <button
              v-if="form.progress < 100"
              type="button"
              class="rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-200"
              @click="form.progress = 100"
            >
              Mark done
            </button>
            <button
              v-if="form.progress > 0"
              type="button"
              class="rounded bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
              @click="form.progress = 0"
            >
              Back to to-do
            </button>
          </div>
        </div>

        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
      </div>

      <div class="mt-4 flex items-center gap-2">
        <button
          type="button"
          :disabled="saving"
          class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          @click="save"
        >
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button
          v-if="task"
          type="button"
          class="ml-auto rounded-lg px-3 py-2 text-sm font-medium"
          :class="
            deleting
              ? 'bg-red-600 text-white'
              : 'text-red-600 hover:bg-red-50'
          "
          @click="remove"
        >
          {{ deleting ? 'Confirm delete?' : 'Delete' }}
        </button>
      </div>
    </div>
  </div>
</template>
