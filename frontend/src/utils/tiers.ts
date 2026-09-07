/** Display metadata for planner tiers (shared by PlanList and the Session screen). */

export const TIER_META: Record<number, { label: string; cls: string }> = {
  1: { label: 'Urgent', cls: 'bg-rose-100 text-rose-700' },
  2: { label: 'In progress', cls: 'bg-amber-100 text-amber-700' },
  3: { label: 'Fits', cls: 'bg-emerald-100 text-emerald-700' },
  4: { label: "Doesn't fit", cls: 'bg-gray-100 text-gray-500' },
}

export function tierMeta(tier: number) {
  return TIER_META[tier] ?? TIER_META[4]
}
