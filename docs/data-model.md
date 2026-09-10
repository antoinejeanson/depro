# Data model (SQLite / SQLAlchemy 2)

```
users           id, email (unique), password_hash (argon2), created_at
sessions        id, user_id, token_hash, expires_at, created_at
                # DB-backed sessions, httpOnly cookie, default 30 days

tasks           user_id FK → users
  id            uuid pk
  title         str
  notes         str | null
  priority      int 0-9 | null
  due_at        datetime | null
  status        'todo' | 'in_progress' | 'done'
  progress      int 0-100        # todo=0, done=100, in_progress=1..99
  estimated_minutes int | null
  recurrence    json | null      # {"frequency":"weekly","interval":1,"weekdays":[1],"day_of_month":null}
  next_due_at   datetime | null  # recurring tasks: eligible again from this moment
  completed_at  datetime | null
  created_at / updated_at

tags            user_id, id, name (unique per user)
task_tags       task_id, tag_id

task_dependencies
  child_id, parent_id            # child needs ALL parents done
                                 # cycles rejected on write

timebox_series  user_id, id, title, rule json, active bool
                # rule: {"frequency":"weekly","interval":1,"weekdays":[1],
                #        "start_time":"19:00","end_time":"21:00"}
timeboxes       user_id, id, series_id | null, starts_at, ends_at, title | null
```

Notes:
- Datetimes are **naive local time** (no tz logic).
- **Plans are not stored.** A plan is a pure function of (tasks, timebox,
  now), computed on demand — see [spec.md](spec.md).
- Every user-owned row carries `user_id`; all queries are scoped to the
  current user. That's what future household sharing builds on.
- Recurrence rule as a JSON column keeps the schema simple; validated in
  Pydantic.
- No migrations: `Base.metadata.create_all` on startup. Adding a column does
  not update an existing dev DB — delete the database file to reset.
