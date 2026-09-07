"""Timebox series occurrence math (pure functions, heavily tested)."""

import re
from datetime import date, datetime, time, timedelta

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_hm(value: str) -> time:
    """Parse 'HH:MM' (24h) into a datetime.time."""
    m = _TIME_RE.match(value)
    if not m:
        raise ValueError(f"invalid time {value!r}, expected HH:MM (24h)")
    return time(int(m.group(1)), int(m.group(2)))


def matches_rule(day: date, rule: dict) -> bool:
    """Does this date match the series rule (ignoring interval)?"""
    frequency = rule["frequency"]
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return day.weekday() in rule["weekdays"]
    if frequency == "monthly":
        return day.day == rule["day_of_month"]
    raise ValueError(f"unknown frequency {frequency!r}")


def series_occurrences(
    rule: dict,
    anchor: date,
    range_start: date,
    range_end: date,
) -> list[tuple[date, datetime, datetime]]:
    """All occurrences of a series rule in [range_start, range_end).

    Occurrence #0 is the first rule match on/after `anchor`; with interval N,
    occurrences 0, N, 2N, ... exist. Returns (date, starts_at, ends_at) tuples.
    """
    if anchor >= range_end:
        return []
    start_hm = parse_hm(rule["start_time"])
    end_hm = parse_hm(rule["end_time"])
    interval = max(1, rule["interval"])
    out: list[tuple[date, datetime, datetime]] = []
    day = anchor
    index = 0
    while day < range_end:
        if matches_rule(day, rule):
            if index % interval == 0 and day >= range_start:
                out.append(
                    (day, datetime.combine(day, start_hm), datetime.combine(day, end_hm))
                )
            index += 1
        day += timedelta(days=1)
    return out


def first_occurrence_date(rule: dict, on_or_after: date) -> date:
    """First rule match on/after the given date (used as the default anchor)."""
    day = on_or_after
    for _ in range(400):
        if matches_rule(day, rule):
            return day
        day += timedelta(days=1)
    raise ValueError("no rule occurrence within 400 days")
