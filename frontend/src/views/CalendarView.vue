<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'

import MonthGrid from '../components/MonthGrid.vue'
import SeriesDialog from '../components/SeriesDialog.vue'
import TimeboxDialog from '../components/TimeboxDialog.vue'
import { useTimeboxesStore, type Series, type Timebox } from '../stores/timeboxes'
import { describeRule, monthCells } from '../utils/calendar'

const store = useTimeboxesStore()
const cursor = ref(dayjs()) // any day in the displayed month

const cells = computed(() =>
  monthCells(cursor.value.year(), cursor.value.month(), store.timeboxes),
)
const rangeStart = computed(() => cells.value[0]?.date ?? '')
const rangeEnd = computed(() => {
  const last = cells.value[41]?.date
  return last ? dayjs(last).add(1, 'day').format('YYYY-MM-DD') : ''
})

async function load() {
  if (!rangeStart.value) return
  await Promise.all([
    store.loadRange(rangeStart.value, rangeEnd.value),
    store.fetchSeries(),
  ])
}

onMounted(load)
watch([rangeStart, rangeEnd], load)

const monthLabel = computed(() =>
  cursor.value.format('MMMM YYYY'),
)

function shiftMonth(delta: number) {
  cursor.value = cursor.value.add(delta, 'month')
}

// Dialogs
const timeboxDialog = ref<{ date: string; timebox?: Timebox } | null>(null)
const seriesDialog = ref<Series | 'new' | null>(null)
const deletingSeries = ref<string | null>(null)
const dialogKey = ref(0)

function openDay(date: string) {
  timeboxDialog.value = { date }
}

function openTimebox(tb: Timebox) {
  // Both one-offs and series occurrences show their plan. Series
  // occurrences cannot be edited or deleted individually — the dialog
  // offers "Edit series" instead.
  timeboxDialog.value = { date: tb.starts_at.slice(0, 10), timebox: tb }
}

function editSeries(seriesId: string) {
  const series = store.series.find((s) => s.id === seriesId)
  if (series) {
    seriesDialog.value = series
  } else {
    timeboxDialog.value = null
  }
}

// After a series save, future occurrences are regenerated with new ids, so
// re-resolve the open occurrence (or close the dialog if it no longer exists).
function closeSeriesDialog() {
  seriesDialog.value = null
  const tb = timeboxDialog.value?.timebox
  if (tb?.series_id) {
    const date = tb.starts_at.slice(0, 10)
    const fresh = store.timeboxes.find(
      (x) => x.series_id === tb.series_id && x.starts_at.slice(0, 10) === date,
    )
    if (!fresh) {
      timeboxDialog.value = null
    } else if (fresh.id !== tb.id) {
      timeboxDialog.value = { date, timebox: fresh }
      dialogKey.value++ // remount so the plan preview refetches
    }
  }
}

function openSeries(series: Series | 'new') {
  seriesDialog.value = series
}

async function toggleSeries(s: Series) {
  await store.updateSeries(s.id, {
    title: s.title,
    rule: s.rule,
    active: !s.active,
  })
}

async function removeSeries(s: Series) {
  if (deletingSeries.value !== s.id) {
    deletingSeries.value = s.id
    window.setTimeout(() => {
      if (deletingSeries.value === s.id) deletingSeries.value = null
    }, 3000)
    return
  }
  deletingSeries.value = null
  await store.deleteSeries(s.id)
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">Calendar</h1>
      <button
        type="button"
        class="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        @click="openDay(cursor.format('YYYY-MM-DD'))"
      >
        + Timebox
      </button>
    </div>

    <div class="mt-4 flex items-center justify-between">
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          aria-label="Previous month"
          @click="shiftMonth(-1)"
        >
          ‹
        </button>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          aria-label="Next month"
          @click="shiftMonth(1)"
        >
          ›
        </button>
        <button
          type="button"
          class="ml-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          @click="cursor = dayjs()"
        >
          Today
        </button>
      </div>
      <h2 class="text-sm font-semibold text-gray-700 sm:text-base">{{ monthLabel }}</h2>
    </div>

    <div class="mt-3">
      <MonthGrid :cells="cells" @day-click="openDay" @timebox-click="openTimebox" />
    </div>

    <section class="mt-6">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Series</h2>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          @click="openSeries('new')"
        >
          + New series
        </button>
      </div>

      <ul v-if="store.series.length" class="mt-3 space-y-2">
        <li
          v-for="s in store.series"
          :key="s.id"
          class="flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3"
        >
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-gray-900">
              {{ s.title }}
              <span v-if="!s.active" class="text-xs font-normal text-gray-400">(paused)</span>
            </p>
            <p class="text-xs text-gray-500">{{ describeRule(s.rule) }}</p>
          </div>
          <button
            type="button"
            class="rounded-lg px-2.5 py-1.5 text-xs font-medium"
            :class="
              s.active
                ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            "
            @click="toggleSeries(s)"
          >
            {{ s.active ? 'Pause' : 'Resume' }}
          </button>
          <button
            type="button"
            class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
            @click="openSeries(s)"
          >
            Edit
          </button>
          <button
            type="button"
            class="rounded-lg px-2.5 py-1.5 text-xs font-medium"
            :class="
              deletingSeries === s.id
                ? 'bg-red-600 text-white'
                : 'text-red-600 hover:bg-red-50'
            "
            @click="removeSeries(s)"
          >
            {{ deletingSeries === s.id ? 'Confirm?' : 'Delete' }}
          </button>
        </li>
      </ul>
      <p v-else class="mt-3 text-sm text-gray-500">
        No series yet — create one to repeat a timebox every week.
      </p>
    </section>

    <TimeboxDialog
      v-if="timeboxDialog"
      :key="dialogKey"
      :date="timeboxDialog.date"
      :timebox="timeboxDialog.timebox ?? null"
      @close="timeboxDialog = null"
      @edit-series="editSeries"
    />
    <SeriesDialog
      v-if="seriesDialog !== null"
      :series="seriesDialog === 'new' ? null : seriesDialog"
      @close="closeSeriesDialog"
    />
  </div>
</template>
