<script setup lang="ts">
import type { PlanEntry } from '../stores/timeboxes'
import { tierMeta } from '../utils/tiers'

defineProps<{ entries: PlanEntry[] }>()
</script>

<template>
  <ul class="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
    <li
      v-for="entry in entries"
      :key="entry.task.id"
      class="flex items-center gap-3 px-3 py-2.5"
    >
      <span
        class="w-20 shrink-0 rounded-md px-1.5 py-0.5 text-center text-xs font-semibold"
        :class="tierMeta(entry.tier).cls"
      >
        {{ tierMeta(entry.tier).label }}
      </span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-gray-900">{{ entry.task.title }}</p>
        <p class="truncate text-xs text-gray-500">{{ entry.reason }}</p>
      </div>
      <span v-if="entry.task.estimated_minutes" class="shrink-0 text-xs text-gray-400">
        {{ entry.task.estimated_minutes }}m
      </span>
    </li>
  </ul>
</template>
