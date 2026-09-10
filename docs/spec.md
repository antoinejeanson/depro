# depro — Product specification

A self-hostable to-do app for recovering procrastinators. One list of tasks,
plus timeboxes that tell the user *exactly what to do* — eliminating decision
paralysis.

## Product summary

- **Tasks**: single list. Optional tags, priority (0–9), due date, progress
  (to-do / in-progress % / done), estimated duration, recurrence, precedence.
- **Timeboxes**: calendar of committed work blocks. One-off, regularly spaced
  (series), or spontaneous ("I have 2h now"). Each timebox gets a generated,
  ordered plan of tasks chosen by a cold algorithm (priority, due date,
  estimate, and precedence) — so the user never has to decide what to do next.
- **Core UX promise**: at any moment, the app shows one "do this now" task.
- **Multi-user**: accounts (email + password); all data per-user. Schema
  prepared for future household sharing.

## Planner algorithm (the core design decision)

**Eligible** = not done, AND (no `next_due_at` or `next_due_at <= now`),
AND all parents done.

**Ordering — four tiers, in order:**

| Tier | What | Sort within tier |
|------|------|------------------|
| T1 | **Overdue / due today** (due_at ≤ end of today) | due_at ↑, priority ↓ (null last), created ↑ |
| T2 | **In progress** | progress ↓ (closest to done first), priority ↓ (null last), created ↑ |
| T3 | **To-do, fits remaining capacity** (est ≤ remaining, or est unknown) | priority ↓ (null = lowest), due_at ↑ (null last), est ↑ (null last), created ↑ |
| T4 | **To-do, doesn't fit** (est > remaining) | priority ↓, due_at ↑ (null last), created ↑ |

**Fill rule**: greedily take tasks T1→T4 until the sum of planned estimates
≥ timebox duration, or no eligible tasks remain. "Remaining" shrinks as tasks
are added (a 90-min task in a 2h box leaves 30 min; a 45-min task then goes
to T4). Unknown estimates count as 0 min but are still added.

**Rationale for the defaults** (all tunable later):
- Due dates are the one hard commitment → they beat everything, including
  momentum.
- In-progress before fresh to-do: finishing what you started is the
  lowest-friction action; "closest to done first" gives a near-term reward.
- "Fits" before "doesn't fit": completing something inside the box is the
  dopamine loop this app is built on.
- Unknown priority = 0 (lowest): optional attributes must not fake urgency.
- Ties broken by creation date (FIFO) so output is deterministic.

**Explainability**: every plan entry gets a `reason` string
("Overdue (due Jun 3)", "In progress — 60%", "Priority 8, fits in 45 min")
shown in the UI. Cheap, and directly serves "why am I doing this?".

**Plan dynamics — the plan is a live projection, not an artifact**:
- The plan is **never stored and never user-editable**. `GET plan` runs the
  algorithm at request time against the current task state. Add a task, bump
  a priority, complete a parent → the next render reflects it instantly.
  If a task should move, change its attributes — that's the only interface.
- No reordering, no skip/remove, no "re-plan" button. The only task actions
  are attribute edits and progress (in-progress %, complete).
- "Top-up on completion" falls out for free: completing the current task
  just shifts the live plan to the next eligible task.
- **Current task** = first entry of the live plan.
- Frontend refetches the plan after any task mutation, and every minute for
  an active box (so "remaining capacity" shrinkage is reflected).
- Upcoming boxes show a live *preview* (current task state, full duration).
  Past boxes show no plan — instead, the tasks completed during that window.

## Recurrence (tasks)

- Rule: `daily` / `weekly` (weekday set) / `monthly` (day of month), each with
  `interval` (every N). No cron-style complexity.
- On completion of a recurring task: reset to `todo`, progress 0,
  `next_due_at` = next occurrence **strictly after now**, computed from the
  completion moment (no drift, no backlog stacking — a missed occurrence just
  means the task stays eligible immediately).
- A recurring task with a future `next_due_at` appears in the list with a
  "next: Mon 19:00" badge but is not planner-eligible until then.

## Precedence

- A task may have multiple parents; it is eligible only when **all** are done.
- Cycle detection (DFS) on write; self-dependency rejected.
- UI: blocked tasks show a lock + parent names.
- Planner never auto-selects blocked tasks; the user **can** manually start
  one (override) — friction-minimizing, but the algorithm stays honest.

## Timeboxes

- **One-off**: create with start/end (calendar click or form).
- **Series**: rule like "every Monday 19:00–21:00". Occurrences are
  **materialized lazily** when a calendar range is loaded (past + future).
  Editing a series regenerates future occurrences; past ones are kept.
- **Spontaneous**: `POST /timeboxes/spontaneous {minutes}` → timebox
  now→now+minutes, plan computed on open.
- **Active** = `starts_at ≤ now ≤ ends_at`. The Session screen shows the
  active timebox (or "start a spontaneous session" otherwise).

## UI

- **Auth**: login / register screens; route guard when no session (the cookie
  is handled by the browser — no token juggling in JS).
- **Tasks**: list with filters (tag/status/search) + add/edit. Desktop: modal
  editor. Mobile: full-screen editor.
- **Calendar**: month grid (PC) / month + day detail (mobile); timebox chips
  per day; series management; click → plan preview.
- **Session**: big "current task" card, progress controls (slider / +10% /
  done), queue below, "start spontaneous session" when idle.
- Navigation: bottom tab bar on mobile, sidebar on desktop.

## Decisions (resolved)

- **Multi-user with accounts**: email + password (argon2), DB-backed sessions
  in httpOnly cookies (30 days). All data per-user; schema prepared for
  future household sharing.
- Planner tier order confirmed: due-today/overdue beats in-progress;
  missing priority = 0.
- **Plans are live projections**: not stored, not user-editable. The only way
  to influence a plan is to change a task's attributes.
- Recurrence stays simple: daily/weekly/monthly × every N.
- Blocked tasks can be manually advanced in the task list; the planner
  ignores them.
- MVP is online only (no PWA/offline). English only.
