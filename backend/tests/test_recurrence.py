"""Unit tests for task recurrence math (pure functions)."""

from datetime import datetime

from app.recurrence import next_occurrence

# Anchor: Monday 2026-09-07 19:00.
ANCHOR = datetime(2026, 9, 7, 19, 0, 0)
DAILY = {"frequency": "daily", "interval": 1}
DAILY_2 = {"frequency": "daily", "interval": 2}
WEEKLY_MON = {"frequency": "weekly", "interval": 1, "weekdays": [0]}
BIWEEKLY_MON = {"frequency": "weekly", "interval": 2, "weekdays": [0]}
MONTHLY_15 = {"frequency": "monthly", "interval": 1, "day_of_month": 15}
MONTHLY_31 = {"frequency": "monthly", "interval": 1, "day_of_month": 31}


def dt(s):
    return datetime.fromisoformat(s)


# ---------------------------------------------------------------- daily


def test_daily_completion_before_occurrence_same_day():
    # Completed 1h before the 19:00 occurrence: it is still later today.
    assert next_occurrence(DAILY, ANCHOR, dt("2026-09-07T18:00")) == dt("2026-09-07T19:00")


def test_daily_completion_after_occurrence_next_day():
    assert next_occurrence(DAILY, ANCHOR, dt("2026-09-07T19:00")) == dt("2026-09-08T19:00")
    assert next_occurrence(DAILY, ANCHOR, dt("2026-09-07T20:00")) == dt("2026-09-08T19:00")


def test_daily_interval_2():
    # Occurrences: 09-07, 09-09, 09-11, ...
    assert next_occurrence(DAILY_2, ANCHOR, dt("2026-09-07T18:00")) == dt("2026-09-07T19:00")
    assert next_occurrence(DAILY_2, ANCHOR, dt("2026-09-07T20:00")) == dt("2026-09-09T19:00")
    assert next_occurrence(DAILY_2, ANCHOR, dt("2026-09-09T19:00")) == dt("2026-09-11T19:00")


# ---------------------------------------------------------------- weekly


def test_weekly_monday():
    # Completed Wednesday: next Monday.
    assert next_occurrence(WEEKLY_MON, ANCHOR, dt("2026-09-09T10:00")) == dt("2026-09-14T19:00")
    # Completed on the Monday occurrence hour: strictly after -> next Monday.
    assert next_occurrence(WEEKLY_MON, ANCHOR, dt("2026-09-14T19:00")) == dt("2026-09-21T19:00")
    # Completed Monday 18:00 (before the 19:00 occurrence): same day.
    assert next_occurrence(WEEKLY_MON, ANCHOR, dt("2026-09-14T18:00")) == dt("2026-09-14T19:00")


def test_weekly_multiple_weekdays():
    # Mon+Wed, interval 1: occurrences Mon 09-07, Wed 09-09, Mon 09-14, ...
    rule = {"frequency": "weekly", "interval": 1, "weekdays": [0, 2]}
    assert next_occurrence(rule, ANCHOR, dt("2026-09-07T18:00")) == dt("2026-09-07T19:00")
    assert next_occurrence(rule, ANCHOR, dt("2026-09-07T20:00")) == dt("2026-09-09T19:00")
    assert next_occurrence(rule, ANCHOR, dt("2026-09-09T20:00")) == dt("2026-09-14T19:00")


def test_biweekly_alignment_kept():
    # Every 2 weeks from the anchor: 09-07, 09-21, 10-05, ...
    assert next_occurrence(BIWEEKLY_MON, ANCHOR, dt("2026-09-07T20:00")) == dt("2026-09-21T19:00")
    assert next_occurrence(BIWEEKLY_MON, ANCHOR, dt("2026-09-21T18:00")) == dt("2026-09-21T19:00")
    assert next_occurrence(BIWEEKLY_MON, ANCHOR, dt("2026-09-21T20:00")) == dt("2026-10-05T19:00")


def test_weekly_anchor_not_on_weekday():
    # Anchor Wednesday 09-09; rule Monday. Occurrences: 09-09 (anchor), 09-14, 09-21...
    anchor = dt("2026-09-09T09:00")
    assert next_occurrence(WEEKLY_MON, anchor, dt("2026-09-08T00:00")) == dt("2026-09-09T09:00")
    assert next_occurrence(WEEKLY_MON, anchor, dt("2026-09-09T09:00")) == dt("2026-09-14T09:00")


# ---------------------------------------------------------------- monthly


def test_monthly_day_15():
    anchor = dt("2026-01-15T09:00")
    assert next_occurrence(MONTHLY_15, anchor, dt("2026-01-15T09:00")) == dt("2026-02-15T09:00")
    assert next_occurrence(MONTHLY_15, anchor, dt("2026-02-10T00:00")) == dt("2026-02-15T09:00")
    assert next_occurrence(MONTHLY_15, anchor, dt("2026-12-01T00:00")) == dt("2026-12-15T09:00")


def test_monthly_day_31_skips_short_months():
    # Jan 31, Mar 31, May 31, Jul 31, Aug 31, Oct 31, Dec 31 (no Feb/Apr/...)
    anchor = dt("2026-01-31T09:00")
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-01-31T09:00")) == dt("2026-03-31T09:00")
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-03-31T09:00")) == dt("2026-05-31T09:00")
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-11-01T00:00")) == dt("2026-12-31T09:00")


def test_monthly_interval_2():
    rule = {"frequency": "monthly", "interval": 2, "day_of_month": 15}
    anchor = dt("2026-01-15T09:00")
    # Jan 15, Mar 15, May 15, ...
    assert next_occurrence(rule, anchor, dt("2026-01-15T09:00")) == dt("2026-03-15T09:00")
    assert next_occurrence(rule, anchor, dt("2026-03-15T09:00")) == dt("2026-05-15T09:00")


# ---------------------------------------------------------------- edge cases


def test_completion_before_anchor_returns_anchor():
    # Early completion: the first occurrence is the anchor itself.
    assert next_occurrence(WEEKLY_MON, ANCHOR, dt("2026-09-01T00:00")) == ANCHOR
    assert next_occurrence(DAILY, ANCHOR, dt("2026-09-07T00:00")) == ANCHOR


def test_late_completion_no_backlog():
    # A daily task completed 5 years late: just the next occurrence, no catch-up.
    anchor = dt("2026-01-01T09:00")
    late = dt("2031-06-01T08:00")
    assert next_occurrence(DAILY, anchor, late) == dt("2031-06-01T09:00")
    late_monthly = dt("2031-06-01T00:00")
    assert next_occurrence(MONTHLY_15, anchor, late_monthly) == dt("2031-06-15T09:00")


def test_anchor_time_preserved():
    # The occurrence time is always the anchor's time of day.
    anchor = dt("2026-01-31T23:30")
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-02-01T00:00")).time() == anchor.time()
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-02-01T00:00")) == dt("2026-03-31T23:30")


def test_year_boundary():
    anchor = dt("2026-12-31T09:00")
    assert next_occurrence(DAILY, anchor, dt("2026-12-31T09:00")) == dt("2027-01-01T09:00")
    assert next_occurrence(MONTHLY_31, anchor, dt("2026-12-31T09:00")) == dt("2027-01-31T09:00")
