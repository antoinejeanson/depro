# AGENTS.md

Guidance for AI coding agents working in this repository.
Human-facing docs: [README.md](README.md). Full product design: [PLAN.md](PLAN.md).

## Project

**depro** ("deprocrastinator") — a self-hostable to-do app for recovering
procrastinators. Core value: eliminate decision paralysis by telling the user
exactly what to do. Two halves:

- **Tasks** — a single to-do list: optional tags, priority 0–9, due date,
  progression (to-do / in-progress % / done), estimated minutes, recurrence,
  and precedence (parent tasks).
- **Timeboxes** — a calendar of committed work blocks (one-off, regularly
  spaced series, or spontaneous "I have 2 h now"). Each timebox gets a plan:
  an ordered list of tasks chosen by a cold algorithm.

### Core product rules (do not break)

- **Plans are live projections**: a pure function of `(tasks, timebox, now)`,
  computed at request time. Never stored, never user-editable. The only way to
  influence a plan is to change a task's attributes (priority, due date,
  estimate, status, parents, recurrence).
- **The planner is cold**: no learning, no personalization, no history.
- **Blocked tasks** (at least one parent not done) are excluded from plans in
  every tier. Users can still advance them manually in the task list.
- **Recurrence**: completing a recurring task flips it back to to-do (progress
  reset) and reschedules `next_due_at` to the next occurrence *strictly after*
  the completion moment. No backlog accumulation, no drift. A recurring task is
  planner-eligible only once `next_due_at <= now`.

## Repository layout

```
backend/    FastAPI + SQLAlchemy 2 + SQLite (uv-managed Python 3.13)
frontend/   Vue 3 + Vite + TypeScript + Pinia + vue-router + Tailwind CSS v4
PLAN.md     Product design (data model, planner algorithm, API, milestones)
Makefile    Dev shortcuts (backend / frontend / test / lint)
```

## Commands

Backend (from `backend/`):

```sh
uv sync                                  # install deps (uv-managed)
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                           # tests
uv run ruff check .                     # lint
```

Frontend (from `frontend/`):

```sh
npm install
npm run dev                             # Vite dev server on :5173, proxies /api → :8000
npx vitest run                          # tests
npm run build                           # vue-tsc type-check + production build
```

Root: `make backend`, `make frontend`, `make test`, `make lint`.

## Backend architecture (`backend/app/`)

- `main.py` — FastAPI app. All routers mounted under `/api`. `init_db()` runs
  in the lifespan. `/api/health` liveness probe.
- `models.py` — SQLAlchemy 2 models. UUID primary keys are assigned at
  construction (`id=uuid.uuid4()`), not at flush time.
- `db.py` — engine + `SessionLocal` + `init_db()` (`Base.metadata.create_all`,
  **no migrations**). Adding a column to a model does not update an existing
  dev DB — delete `backend/data/depro.db` (gitignored) to reset.
- `schemas.py` — Pydantic v2 request/response models.
- `routers/` — `auth`, `tasks`, `tags`, `timeboxes` (exports two routers:
  `timeboxes_router` and `series_router`), `export`.
- `planner.py` — **pure** planner (no DB access). See "Planner" below.
- `recurrence.py` — **pure** next-occurrence math.
- `task_service.py` — `apply_progress` / `complete_task`; the recurring-task
  completion flip lives here (both the `/progress` and `/complete` endpoints go
  through it).
- `timebox_service.py` — series occurrence math (materialization).

### Conventions

- **Naive local datetimes everywhere** — no UTC, no timezone conversion. The
  frontend sends `YYYY-MM-DDTHH:mm:ss` (no offset); the backend stores it as-is.
- **User scoping**: every query filters by `user_id`. Cross-user access
  returns **404**, not 403.
- **Auth**: argon2 password hashes; DB-backed sessions storing SHA-256 of the
  token; httpOnly `SameSite=Lax` cookie, 30 days; `get_current_user` dependency
  in `deps.py`.
- **Ruff**: line length 100; import order is enforced (`app.db` sorts before
  `app.deps`).
- **`JSONResponse` needs `jsonable_encoder`** for UUID/datetime/pydantic values
  (see `routers/export.py`) — plain `json.dumps` chokes on them.
- Pydantic ignores extra fields: the frontend round-trips full `TaskRead` JSON
  in PUT bodies; `TaskUpdate`/`TaskCreate` pick what they know.
- `TaskUpdate.parents` **replaces** the parent set; `recurrence: null` clears
  `next_due_at`; changing the rule or `due_at` re-anchors `next_due_at`.
- Response orderings are deterministic: task tags sorted by name, `TaskRead`
  parents sorted by (title, id).
- Route ordering matters: `GET /timeboxes/now` is declared before the
  `/{timebox_id}` routes.

### Planner (the heart of the app)

`plan_timebox(tasks, timebox, now, blocked)` → ordered `PlanItem(task, tier,
reason)`. Eligible = not done AND (`next_due_at` is None or `<= now`) AND not
in `blocked`. Tiers, in order:

1. Overdue / due today (`due_at <= end of today`) — always included.
2. In progress — always included.
3. To-do that fits remaining capacity (est ≤ remaining; unknown est = 0 min,
   still included).
4. To-do that doesn't fit (shown in full, as the "doesn't fit" queue).

Fill rule: T1/T2 always included and shrink remaining capacity; to-dos are
walked in sort order (priority ↓ nulls-last, due ↑ nulls-last, est ↑
nulls-last, created ↑, id) and each either fits (T3, shrinks remaining) or
doesn't (T4, remaining unchanged). Capacity = full duration for upcoming
boxes, *remaining wall-clock* (`ends_at - now`) for active boxes, none for
past boxes (past boxes return the list of tasks completed inside the window
instead).

## Frontend architecture (`frontend/src/`)

- `api/client.ts` — minimal fetch wrapper (`ApiError`); same-origin cookies.
- `stores/` — Pinia stores mirroring the API: `auth`, `tasks`, `timeboxes`,
  `session`.
- `views/` — `TasksView`, `CalendarView`, `SessionView`, `LoginView`,
  `RegisterView`.
- `components/` — `TaskItem`, `TaskEditor`, `MonthGrid`, `TimeboxDialog`,
  `SeriesDialog`, `PlanList`, `icons/`.
- `utils/` — `calendar.ts` (month-grid cells, rule descriptions), `tiers.ts`
  (planner-tier display metadata shared by `PlanList` and the Session screen).
- **No calendar library** — `MonthGrid` is a custom 7-column grid.
- **Tailwind v4** — no config file; `@import "tailwindcss"` in `style.css`.
- **Mobile-first**: bottom tab bar + top bar on small screens, left sidebar on
  `md:` and up; dialogs are bottom sheets on mobile (`items-end` →
  `sm:items-center`), scrollable with `max-h-full`.
- Datetimes: naive local ISO strings; `dayjs` for formatting.
- **TypeScript `erasableSyntaxOnly`** — no parameter properties or other
  non-erasable syntax.

## Testing

- **Backend** (`backend/tests/`): pytest + FastAPI `TestClient`. `conftest.py`
  provides a per-test in-memory SQLite (StaticPool) wired in via
  `app.dependency_overrides[get_db]`. Planner and recurrence math have pure
  unit tests; API tests cover auth, scoping, and validation.
- **Frontend** (`frontend/src/__tests__/`): vitest + `@vue/test-utils`. Stub
  `fetch` with `vi.stubGlobal('fetch', vi.fn(...))`; create a fresh pinia per
  test (`setActivePinia(createPinia())`); views that use `RouterLink` need a
  router plugin (`createRouter` + `createMemoryHistory`).
- **Keep tests deterministic**: never assert exact wall-clock-dependent values
  — use far-past anchors and property assertions (e.g. "next occurrence is a
  Monday at 09:00, in the future").

## Environment quirks

- No system Python — `uv` provisions a managed CPython 3.13.
- `ps` / `pkill` / `pgrep` are unavailable in this environment — scan
  `/proc/[0-9]*/cmdline` to find processes.
- Dev servers: backend `:8000`, frontend `:5173` (Vite proxies `/api` →
  `:8000`). Dev data lives in `backend/data/depro.db` (gitignored).
