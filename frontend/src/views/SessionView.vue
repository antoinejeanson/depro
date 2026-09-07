<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import PlanList from '../components/PlanList.vue'
import { RouterLink } from 'vue-router'
import { useSessionStore } from '../stores/session'
import { useTasksStore } from '../stores/tasks'
import { tierMeta } from '../utils/tiers'

const session = useSessionStore()
const tasks = useTasksStore()

// Ticking clock for the countdown; the plan refetches every minute while active.
const now = ref(new Date())
let clockTimer: number | undefined
let pollTimer: number | undefined

const box = computed(() => session.now?.timebox ?? null)
const active = computed(() => session.now?.state === 'active' && box.value !== null)
const current = computed(() => session.now?.current ?? null)
const queue = computed(() => (session.now?.plan ?? []).slice(1))

const remainingMs = computed(() => {
  if (!box.value) return 0
  return Math.max(0, new Date(box.value.ends_at).getTime() - now.value.getTime())
})

const remainingLabel = computed(() => {
  const total = Math.floor(remainingMs.value / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
})

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function refresh() {
  await session.fetchNow()
  await tasks.fetchTasks()
}

onMounted(() => {
  refresh()
  clockTimer = window.setInterval(() => (now.value = new Date()), 1000)
  pollTimer = window.setInterval(() => {
    if (active.value) refresh()
  }, 60_000)
})

onBeforeUnmount(() => {
  window.clearInterval(clockTimer)
  window.clearInterval(pollTimer)
})

// --- current task controls -------------------------------------------------

const draft = ref(0)
watch(current, () => {
  draft.value = current.value?.task.progress ?? 0
})

async function commitProgress() {
  const t = current.value?.task
  if (!t || draft.value === t.progress) return
  await tasks.setProgress(t.id, draft.value)
  await session.fetchNow()
}

async function bumpProgress() {
  const t = current.value?.task
  if (!t) return
  const next = Math.min(100, t.progress + 10)
  draft.value = next
  await tasks.setProgress(t.id, next)
  await session.fetchNow()
}

async function completeCurrent() {
  const t = current.value?.task
  if (!t) return
  await tasks.completeTask(t.id)
  await session.fetchNow()
}

// --- spontaneous start ------------------------------------------------------

const QUICK = [30, 45, 60, 90, 120]
const minutes = ref(60)
const starting = ref(false)

async function start() {
  starting.value = true
  try {
    await session.startSpontaneous(minutes.value)
  } finally {
    starting.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold text-gray-900">Session</h1>

    <!-- Active timebox -->
    <template v-if="active && box">
      <div class="mt-4 flex items-center justify-between gap-3 rounded-xl bg-indigo-50 px-4 py-3">
        <div class="min-w-0">
          <p class="truncate font-medium text-indigo-900">{{ box.title || 'Timebox' }}</p>
          <p class="text-xs text-indigo-700">
            {{ fmt(box.starts_at) }} → {{ fmt(box.ends_at) }}
          </p>
        </div>
        <p class="text-lg font-semibold tabular-nums text-indigo-900">
          {{ remainingLabel }}
        </p>
      </div>

      <section v-if="current" class="mt-6">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Do this now
        </h2>
        <div class="mt-2 rounded-2xl border-2 border-indigo-600 bg-white p-4 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="text-lg font-semibold text-gray-900">{{ current.task.title }}</p>
              <div class="mt-1 flex flex-wrap items-center gap-1.5">
                <span
                  class="rounded-md px-1.5 py-0.5 text-xs font-semibold"
                  :class="tierMeta(current.tier).cls"
                >
                  {{ tierMeta(current.tier).label }}
                </span>
                <span class="text-sm text-gray-500">{{ current.reason }}</span>
              </div>
            </div>
            <div class="flex shrink-0 gap-1.5">
              <span
                v-if="current.task.priority !== null"
                class="rounded-md bg-indigo-100 px-1.5 py-0.5 text-xs font-semibold text-indigo-700"
              >
                P{{ current.task.priority }}
              </span>
              <span
                v-if="current.task.estimated_minutes"
                class="rounded-md bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600"
              >
                {{ current.task.estimated_minutes }} min
              </span>
              <span
                v-if="current.task.due_at"
                class="rounded-md bg-rose-100 px-1.5 py-0.5 text-xs font-medium text-rose-700"
              >
                due {{ fmt(current.task.due_at) }}
              </span>
            </div>
          </div>

          <div class="mt-4">
            <div class="flex items-center gap-3">
              <input
                :value="draft"
                type="range"
                min="0"
                max="100"
                step="5"
                class="flex-1 accent-indigo-600"
                aria-label="Progress"
                @change="commitProgress"
                @input="draft = Number(($event.target as HTMLInputElement).value)"
              />
              <span class="w-10 text-right text-sm font-medium tabular-nums text-gray-700">
                {{ draft }}%
              </span>
            </div>
            <div class="mt-3 flex gap-2">
              <button
                type="button"
                class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                @click="bumpProgress"
              >
                +10%
              </button>
              <button
                type="button"
                class="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700"
                @click="completeCurrent"
              >
                Done ✓
              </button>
            </div>
          </div>
        </div>
      </section>
      <p v-else class="mt-6 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
        Nothing left in this timebox — the plan is empty. Enjoy the calm.
      </p>

      <section v-if="queue.length" class="mt-6">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-gray-500">
          Up next in this timebox
        </h2>
        <div class="mt-2">
          <PlanList :entries="queue" />
        </div>
      </section>
    </template>

    <!-- Idle: no active timebox -->
    <div v-else class="mt-4 rounded-2xl border border-dashed border-gray-300 bg-white p-6">
      <p class="text-gray-600">No active timebox.</p>
      <h2 class="mt-4 text-sm font-semibold text-gray-900">
        Start a spontaneous session
      </h2>
      <p class="mt-1 text-sm text-gray-500">
        “I have some time now” — the planner fills it for you.
      </p>
      <div class="mt-3 flex flex-wrap gap-2">
        <button
          v-for="m in QUICK"
          :key="m"
          type="button"
          class="rounded-lg border px-3 py-1.5 text-sm font-medium"
          :class="
            minutes === m
              ? 'border-indigo-600 bg-indigo-600 text-white'
              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          "
          @click="minutes = m"
        >
          {{ m }} min
        </button>
        <input
          v-model.number="minutes"
          type="number"
          min="5"
          max="480"
          class="w-24 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
          aria-label="Minutes"
        />
      </div>
      <button
        type="button"
        :disabled="starting || !minutes || minutes < 5"
        class="mt-4 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        @click="start"
      >
        {{ starting ? 'Starting…' : 'Start now' }}
      </button>
      <p class="mt-4 text-sm text-gray-500">
        Or plan ahead:
        <RouterLink to="/calendar" class="font-medium text-indigo-600 hover:underline">
          add a timebox on the calendar
        </RouterLink>
        .
      </p>
    </div>
  </div>
</template>
