# depro

Short for **deprocrastinator**. Self-hostable application for managing the to-do
list of recovering procrastinators through discipline.

The app has two halves:

- **Tasks** — a single to-do list with optional tags, priority (0–9), due
  dates, progress, estimated durations, recurrence and precedence.
- **Timeboxes** — committed work blocks on a calendar (one-off, regularly
  spaced, or spontaneous). Each timebox gets a plan: an ordered list of tasks
  chosen by a cold algorithm (priority, due date, estimated time, precedence)
  so the user never has to decide what to do next.

See [PLAN.md](PLAN.md) for the full design (data model, planner algorithm,
API, milestones).

## Repository layout

```
backend/    FastAPI + SQLAlchemy + SQLite (managed with uv)
frontend/   Vue 3 + Vite + TypeScript + Pinia + Tailwind CSS
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python and backend dependencies)
- Node.js ≥ 20 (frontend)

## Development

Run the backend and frontend in two terminals:

```sh
# Terminal 1 — API on http://localhost:8000 (docs at /docs)
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — web app on http://localhost:5173 (proxies /api → :8000)
cd frontend
npm install
npm run dev
```

Or use the Makefile from the repo root:

```sh
make backend   # uv sync + uvicorn --reload
make frontend  # npm install (if needed) + vite dev
```

## Tests & linting

```sh
cd backend && uv run ruff check . && uv run pytest
cd frontend && npm test && npm run build   # build also type-checks
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M0 | Scaffold (both apps, tooling) | ✅ |
| M1 | Auth (accounts, sessions, user scoping) | ✅ |
| M2 | Tasks (CRUD, tags, list UI) | ✅ |
| M3 | Timeboxes (one-off + series, calendar) | ✅ |
| M4 | Planner & Session (live plans, spontaneous) | ⬜ |
| M5 | Recurrence & Precedence | ⬜ |
| M6 | Polish | ⬜ |

## License

MIT — see [LICENSE](LICENSE).
