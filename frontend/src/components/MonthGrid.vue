<script setup lang="ts">
import dayjs from 'dayjs'

import { WEEKDAY_NAMES, type DayCell } from '../utils/calendar'
import type { Timebox } from '../stores/timeboxes'

defineProps<{ cells: DayCell[] }>()
const emit = defineEmits<{
  (e: 'day-click', date: string): void
  (e: 'timebox-click', timebox: Timebox): void
}>()

function chipTime(tb: Timebox) {
  return `${dayjs(tb.starts_at).format('HH:mm')}–${dayjs(tb.ends_at).format('HH:mm')}`
}

function chipLabel(tb: Timebox) {
  return tb.title || tb.series_title || 'Timebox'
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
    <div
      class="grid grid-cols-7 border-b border-gray-200 bg-gray-50 text-center text-xs font-semibold text-gray-500"
    >
      <div v-for="w in WEEKDAY_NAMES" :key="w" class="py-2">
        {{ w }}
      </div>
    </div>
    <div class="grid grid-cols-7">
      <div
        v-for="cell in cells"
        :key="cell.date"
        class="min-h-16 cursor-pointer border-b border-r border-gray-100 p-1 transition-colors last:border-r-0 hover:bg-indigo-50/60 sm:min-h-24"
        :class="{ 'bg-gray-50/70': !cell.inMonth }"
        @click="emit('day-click', cell.date)"
      >
        <span
          class="inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-xs"
          :class="
            cell.isToday
              ? 'bg-indigo-600 font-bold text-white'
              : cell.inMonth
                ? 'text-gray-700'
                : 'text-gray-300'
          "
        >
          {{ Number(cell.date.slice(8)) }}
        </span>
        <div class="mt-0.5 space-y-0.5">
          <button
            v-for="tb in cell.timeboxes.slice(0, 3)"
            :key="tb.id"
            type="button"
            class="block w-full truncate rounded px-1 py-0.5 text-left text-[10px] font-medium sm:text-[11px]"
            :class="
              tb.series_id
                ? 'bg-indigo-100 text-indigo-800 hover:bg-indigo-200'
                : 'bg-teal-100 text-teal-800 hover:bg-teal-200'
            "
            :title="`${chipTime(tb)} ${chipLabel(tb)}`"
            @click.stop="emit('timebox-click', tb)"
          >
            {{ chipTime(tb) }} {{ chipLabel(tb) }}
          </button>
          <button
            v-if="cell.timeboxes.length > 3"
            type="button"
            class="block w-full truncate rounded px-1 text-left text-[10px] text-gray-400 hover:bg-gray-100"
            @click.stop="emit('day-click', cell.date)"
          >
            +{{ cell.timeboxes.length - 3 }} more
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
