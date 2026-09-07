import dayjs from 'dayjs'

import type { SeriesRule, Timebox } from '../stores/timeboxes'

export const WEEKDAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** Human summary of a series rule, e.g. "Every 2 weeks on Mon, Wed · 19:00–21:00". */
export function describeRule(rule: SeriesRule): string {
  const times = `${rule.start_time}–${rule.end_time}`
  const every = rule.interval > 1 ? `Every ${rule.interval} ` : ''
  switch (rule.frequency) {
    case 'daily':
      return `${every ? `${every}days` : 'Daily'} · ${times}`
    case 'weekly': {
      const days = rule.weekdays
        .slice()
        .sort((a, b) => a - b)
        .map((w) => WEEKDAY_NAMES[w])
        .join(', ')
      return `${every ? `${every}weeks on ` : ''}${days} · ${times}`
    }
    case 'monthly':
      return `${every ? `${every}months on ` : ''}day ${rule.day_of_month} · ${times}`
  }
}

export interface DayCell {
  date: string // YYYY-MM-DD
  inMonth: boolean
  isToday: boolean
  timeboxes: Timebox[]
}

/**
 * Build the 42 cells (6 weeks, Monday-first) of the month grid around the
 * given month. `timeboxes` are grouped by their start day.
 */
export function monthCells(
  year: number,
  month: number, // 0-11
  timeboxes: Timebox[],
): DayCell[] {
  const first = dayjs().year(year).month(month).date(1)
  const gridStart = first.subtract((first.day() + 6) % 7, 'day') // back to Monday
  const byDay = new Map<string, Timebox[]>()
  for (const tb of timeboxes) {
    const key = dayjs(tb.starts_at).format('YYYY-MM-DD')
    const list = byDay.get(key) ?? []
    list.push(tb)
    byDay.set(key, list)
  }
  const cells: DayCell[] = []
  for (let i = 0; i < 42; i++) {
    const d = gridStart.add(i, 'day')
    const date = d.format('YYYY-MM-DD')
    cells.push({
      date,
      inMonth: d.month() === month,
      isToday: d.isSame(dayjs(), 'day'),
      timeboxes: byDay.get(date) ?? [],
    })
  }
  return cells
}
