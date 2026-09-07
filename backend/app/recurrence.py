"""Task recurrence math (pure functions, heavily tested).

A recurring task's schedule is anchored at its due date (`anchor`):

    occurrences = [anchor] + every `interval`-th rule match strictly after
    the anchor date, at the anchor's time of day.

`next_occurrence` returns the first occurrence strictly after `after`.
There is no drift and no backlog stacking: a missed occurrence is simply
skipped, so a late completion schedules the next occurrence after the
completion moment.
"""

import calendar
from datetime import date, datetime, timedelta


def _ym(d: date) -> int:
    return d.year * 12 + (d.month - 1)


def _from_ym(ym: int) -> tuple[int, int]:
    return ym // 12, ym % 12 + 1


def _first_match_date(freq: str, rule: dict, d: date) -> date:
    """First rule match on/after d."""
    if freq == "daily":
        return d
    if freq == "weekly":
        for i in range(7):
            if (d + timedelta(days=i)).weekday() in rule["weekdays"]:
                return d + timedelta(days=i)
        raise ValueError("weekly rule has no weekdays")
    if freq == "monthly":
        dom = rule["day_of_month"]
        for ym in range(_ym(d), _ym(d) + 12):
            y, m = _from_ym(ym)
            if dom <= calendar.monthrange(y, m)[1]:
                cand = date(y, m, dom)
                if cand >= d:
                    return cand
        raise ValueError("monthly rule never matches")
    raise ValueError(f"unknown frequency {freq!r}")


def _weekly_offsets(first_match: date, weekdays: list[int]) -> list[int]:
    """Offsets i (0..6) where first_match + i days has a weekday in the rule."""
    return [i for i in range(7) if (first_match.weekday() + i) % 7 in weekdays]


def _match_count(freq: str, rule: dict, first_match: date, d: date) -> int:
    """Number of rule matches in [first_match, d] (0 if d < first_match)."""
    if d < first_match:
        return 0
    if freq == "daily":
        return (d - first_match).days + 1
    if freq == "weekly":
        days = (d - first_match).days + 1
        q, rem = divmod(days, 7)
        offsets = _weekly_offsets(first_match, rule["weekdays"])
        return q * len(offsets) + sum(1 for o in offsets if o < rem)
    if freq == "monthly":
        dom = rule["day_of_month"]
        count = 0
        for ym in range(_ym(first_match), _ym(d) + 1):
            y, m = _from_ym(ym)
            if dom <= calendar.monthrange(y, m)[1] and date(y, m, dom) <= d:
                count += 1
        return count
    raise ValueError(f"unknown frequency {freq!r}")


def _match_date(freq: str, rule: dict, first_match: date, m: int) -> date:
    """The m-th (0-indexed) rule match on/after first_match."""
    if freq == "daily":
        return first_match + timedelta(days=m)
    if freq == "weekly":
        offsets = _weekly_offsets(first_match, rule["weekdays"])
        q, r = divmod(m, len(offsets))
        return first_match + timedelta(weeks=q, days=offsets[r])
    if freq == "monthly":
        dom = rule["day_of_month"]
        ym = _ym(first_match)
        while True:
            y, m_ = _from_ym(ym)
            if dom <= calendar.monthrange(y, m_)[1]:
                if m == 0:
                    return date(y, m_, dom)
                m -= 1
            ym += 1
    raise ValueError(f"unknown frequency {freq!r}")


def next_occurrence(rule: dict, anchor: datetime, after: datetime) -> datetime:
    """First scheduled occurrence strictly after `after`.

    The schedule is anchored at `anchor` (the task's due date): the anchor
    itself is occurrence #0, then every `interval`-th rule match strictly
    after the anchor date, at the anchor's time of day.
    """
    if anchor > after:
        return anchor

    freq = rule["frequency"]
    interval = max(1, rule.get("interval", 1))
    # Rule matches strictly after the anchor date, numbered j = 0, 1, 2, ...
    # The anchor is occurrence #0, so a match at index j is kept when
    # (j + 1) % interval == 0 (i.e. every `interval`-th match after it).
    first_after = _first_match_date(freq, rule, anchor.date() + timedelta(days=1))
    # C = number of such matches with date <= after.date(); matches j < C have
    # date <= after.date(), match j = C has date > after.date().
    c = _match_count(freq, rule, first_after, after.date())
    candidates: list[int] = []
    if c >= 1 and c % interval == 0:
        candidates.append(c - 1)  # same-date case: anchor time may beat `after`
    candidates.append(c + ((interval - 1 - c) % interval))
    for j in candidates:
        d = _match_date(freq, rule, first_after, j)
        dt = datetime.combine(d, anchor.time())
        if dt > after:
            return dt
    raise ValueError("unreachable: no occurrence found")
