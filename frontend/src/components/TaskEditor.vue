<script setup lang="ts">
import { reactive, ref } from 'vue'
import dayjs from 'dayjs'

import { useTasksStore, type Task, type TaskPayload } from '../stores/tasks'

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
})
const newTag = ref('')

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

function payload(): TaskPayload {
  return {
    title: form.title.trim(),
    notes: form.notes.trim() || null,
    priority: form.priority,
    // Naive local ISO — matches the backend's naive-local datetime design.
    due_at: form.due_at ? dayjs(form.due_at).format('YYYY-MM-DDTHH:mm:ss') : null,
    estimated_minutes:
      form.estimated_minutes === '' ? null : Number(form.estimated_minutes),
    tags: form.tags,
  }
}

async function save() {
  if (!form.title.trim()) {
    error.value = 'A title is required'
    return
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
