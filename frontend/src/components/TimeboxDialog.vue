<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import PlanList from './PlanList.vue'
import { useTimeboxesStore, type PlanResponse, type Timebox } from '../stores/timeboxes'

const props = defineProps<{ date: string; timebox?: Timebox | null }>()
const emit = defineEmits<{ close: [] }>()

const store = useTimeboxesStore()
const saving = ref(false)
const error = ref('')
const plan = ref<PlanResponse | null>(null)

const form = reactive({
  date: props.date,
  start: '09:00',
  end: '11:00',
  title: '',
})

onMounted(async () => {
  if (props.timebox) {
    try {
      plan.value = await store.fetchPlan(props.timebox.id)
    } catch {
      plan.value = null
    }
  }
})

async function create() {
  if (form.end <= form.start) {
    error.value = 'The end time must be after the start time'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await store.createOneOff({
      title: form.title.trim() || null,
      starts_at: `${form.date}T${form.start}:00`,
      ends_at: `${form.date}T${form.end}:00`,
    })
    emit('close')
  } catch {
    error.value = 'Could not create the timebox. Please try again.'
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.timebox) return
  saving.value = true
  try {
    await store.deleteOneOff(props.timebox.id)
    emit('close')
  } catch {
    error.value = 'Could not delete the timebox. Please try again.'
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
      class="flex max-h-full w-full flex-col overflow-y-auto rounded-t-2xl bg-white p-4 shadow-xl sm:max-w-md sm:rounded-2xl sm:p-6"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">
          {{ timebox ? 'Timebox' : 'New timebox' }}
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

      <!-- Detail mode: existing one-off -->
      <template v-if="timebox">
        <div class="mt-4 space-y-1 text-sm text-gray-700">
          <p class="text-base font-medium text-gray-900">
            {{ timebox.title || 'Timebox' }}
          </p>
          <p>{{ timebox.starts_at.replace('T', ' at ') }}</p>
          <p class="text-gray-500">
            {{
              timebox.ends_at.slice(11, 16)
            }}
            · one-off
          </p>
        </div>

        <div v-if="plan" class="mt-4">
          <template v-if="plan.state === 'past'">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Completed in this timebox
            </h3>
            <ul v-if="plan.completed.length" class="mt-2 space-y-1">
              <li
                v-for="t in plan.completed"
                :key="t.id"
                class="flex items-center gap-2 text-sm text-gray-700"
              >
                <span class="text-emerald-600">✓</span>
                <span class="line-through decoration-gray-400">{{ t.title }}</span>
              </li>
            </ul>
            <p v-else class="mt-2 text-sm text-gray-400">Nothing was completed.</p>
          </template>
          <template v-else>
            <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Plan
            </h3>
            <div v-if="plan.plan.length" class="mt-2">
              <PlanList :entries="plan.plan" />
            </div>
            <p v-else class="mt-2 text-sm text-gray-400">No eligible tasks.</p>
          </template>
        </div>
        <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
        <div class="mt-4 flex items-center gap-2">
          <button
            type="button"
            :disabled="saving"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            Close
          </button>
          <button
            type="button"
            :disabled="saving"
            class="ml-auto rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            @click="remove"
          >
            Delete
          </button>
        </div>
      </template>

      <!-- Create mode -->
      <template v-else>
        <div class="mt-4 space-y-4">
          <label class="block text-sm text-gray-700">
            <span class="mb-1 block">Title (optional)</span>
            <input
              v-model="form.title"
              type="text"
              placeholder="e.g. Deep work"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
          <label class="block text-sm text-gray-700">
            <span class="mb-1 block">Date</span>
            <input
              v-model="form.date"
              type="date"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="text-sm text-gray-700">
              <span class="mb-1 block">Start</span>
              <input
                v-model="form.start"
                type="time"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </label>
            <label class="text-sm text-gray-700">
              <span class="mb-1 block">End</span>
              <input
                v-model="form.end"
                type="time"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </label>
          </div>
          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        </div>
        <div class="mt-4 flex items-center gap-2">
          <button
            type="button"
            :disabled="saving"
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            @click="create"
          >
            {{ saving ? 'Saving…' : 'Create' }}
          </button>
          <button
            type="button"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            @click="emit('close')"
          >
            Cancel
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
