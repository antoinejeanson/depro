# API

REST JSON under `/api`. All endpoints are cookie-authenticated (httpOnly
`SameSite=Lax` session cookie) except the auth endpoints themselves.
Cross-user access returns **404**, not 403.

- `GET /api/health` — liveness probe.

## Auth

- `POST /auth/register` — create account (email + password).
- `POST /auth/login` — start session (sets the cookie).
- `POST /auth/logout` — end session.
- `GET /auth/me` — current user.

## Tasks

- `GET /tasks` — list; filters: `q` (title search), `tag`, `status`.
- `POST /tasks` — create.
- `GET /tasks/{id}` · `PUT /tasks/{id}` · `DELETE /tasks/{id}`
  — `PUT` replaces the tag and parent sets; changing the recurrence rule or
  `due_at` re-anchors `next_due_at`; `recurrence: null` clears it.
- `POST /tasks/{id}/progress` — set progress 0–100 (100 handles the
  recurring-task flip).
- `POST /tasks/{id}/complete` — mark done (same flip).

## Tags

- `GET /tags` — list with open-task counts.
- `POST /tags` — create (409 on duplicate name, case-insensitive).
- `DELETE /tags/{id}`

## Timeboxes

- `GET /timeboxes?start&end` — occurrences in a range (series occurrences
  are materialized on load).
- `POST /timeboxes` — create one-off.
- `POST /timeboxes/spontaneous` — `{minutes}` → box now→now+minutes.
- `GET /timeboxes/now` — active box + live plan + current task (Session
  screen); idle state when no active box.
- `GET /timeboxes/{id}/plan` — live-computed ordered tasks + reasons; past
  boxes return the tasks completed inside the window instead.
- `DELETE /timeboxes/{id}` — one-offs only (409 for series boxes).

## Series

- `GET /timebox-series` · `POST /timebox-series`
- `PUT /timebox-series/{id}` — regenerates future occurrences; past kept.
- `DELETE /timebox-series/{id}`

## Export

- `GET /export` — whole dataset as JSON (tasks, tags, timeboxes, series).
