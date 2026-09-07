<script setup lang="ts">
import { reactive, ref } from 'vue'

import { WEEKDAY_NAMES } from '../utils/calendar'
import { useTimeboxesStore, type Series, type SeriesRule } from '../stores/timeboxes'

const props = defineProps<{ series: Series | null }>()
const emit = defineEmits<{ close: [] }>()

const store = useTimeboxesStore()
const saving = ref(false)
const error = ref('')

const form = reactive({
  title: props.series?.title ?? '',
  frequency: (props.series?.rule.frequency ?? 'weekly') as SeriesRule['frequency'],
  interval: props.series?.rule.interval ?? 1,
  weekdays: [...(props.series?.rule.weekdays ?? [0])],
  day_of_month: props.series?.rule.day_of_month ?? 1,
  start_time: props.series?.rule.start_time ?? '19:00',
  end_time: props.series?.rule.end_time ?? '21:00',
  active: props.series?.active ?? true,
})

function toggleWeekday(w: number) {
  const i = form.weekdays.indexOf(w)
  if (i === -1) form.weekdays.push(w)
  else form.weekdays.splice(i, 1)
}

function rule(): SeriesRule {
  return {
    frequency: form.frequency,
    interval: form.interval,
    weekdays: form.weekdays,
    day_of_month: form.day_of_month,
    start_time: form.start_time,
    end_time: form.end_time,
  }
}

async function save() {
  if (!form.title.trim()) {
    error.value = 'A title is required'
    return
  }
  if (form.weekdays.length === 0) {
    error.value = 'Pick at least one weekday'
    return
  }
  if (form.end_time <= form.start_time) {
    error.value = 'The end time must be after the start time'
    return
  }
  saving.value = true
  error.value = ''
  try {
    if (props.series) {
      await store.updateSeries(props.series.id, {
        title: form.title.trim(),
        rule: rule(),
        active: form.active,
      })
    } else {
      await store.createSeries({ title: form.title.trim(), rule: rule() })
    }
    emit('close')
  } catch {
    error.value = 'Could not save the series. Please try again.'
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
          {{ series ? 'Edit series' : 'New series' }}
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
        <label class="block text-sm text-gray-700">
          <span class="mb-1 block">Title</span>
          <input
            v-model="form.title"
            type="text"
            placeholder="e.g. Evening work"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">Repeats</span>
            <select
              v-model="form.frequency"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">Every</span>
            <input
              v-model.number="form.interval"
              type="number"
              min="1"
              max="365"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
        </div>

        <div v-if="form.frequency === 'weekly'">
          <span class="mb-1 block text-sm text-gray-700">Weekdays</span>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="(name, i) in WEEKDAY_NAMES"
              :key="name"
              type="button"
              class="rounded-lg px-2.5 py-1.5 text-xs font-medium"
              :class="
                form.weekdays.includes(i)
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              "
              @click="toggleWeekday(i)"
            >
              {{ name }}
            </button>
          </div>
        </div>

        <label v-if="form.frequency === 'monthly'" class="block text-sm text-gray-700">
          <span class="mb-1 block">Day of month</span>
          <input
            v-model.number="form.day_of_month"
            type="number"
            min="1"
            max="31"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">Start</span>
            <input
              v-model="form.start_time"
              type="time"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
          <label class="text-sm text-gray-700">
            <span class="mb-1 block">End</span>
            <input
              v-model="form.end_time"
              type="time"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
          </label>
        </div>

        <label v-if="series" class="flex items-center gap-2 text-sm text-gray-700">
          <input
            v-model="form.active"
            type="checkbox"
            class="h-4 w-4 rounded accent-indigo-600"
          />
          Active (paused series stop producing new timeboxes)
        </label>

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
      </div>
    </div>
  </div>
</template>
