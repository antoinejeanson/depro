from datetime import date

from app.timebox_service import first_occurrence_date, parse_hm, series_occurrences


def rule(**overrides):
    base = {
        "frequency": "weekly",
        "interval": 1,
        "weekdays": [0],
        "day_of_month": None,
        "start_time": "19:00",
        "end_time": "21:00",
    }
    base.update(overrides)
    return base


def test_parse_hm():
    assert parse_hm("19:00").hour == 19
    assert parse_hm("00:05").minute == 5
    for bad in ("24:00", "9:00", "19:60", "1900", "19:0", ""):
        try:
            parse_hm(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} should be invalid")


def test_daily_interval():
    r = rule(frequency="daily", interval=2)
    occ = series_occurrences(r, date(2026, 9, 1), date(2026, 9, 1), date(2026, 9, 8))
    expected = [date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 5), date(2026, 9, 7)]
    assert [d for d, _, _ in occ] == expected


def test_weekly_multiple_weekdays():
    r = rule(frequency="weekly", weekdays=[0, 2])  # Mon + Wed
    occ = series_occurrences(r, date(2026, 9, 1), date(2026, 9, 7), date(2026, 9, 21))
    # 2026-09-07 is a Monday
    assert [d for d, _, _ in occ] == [
        date(2026, 9, 7),
        date(2026, 9, 9),
        date(2026, 9, 14),
        date(2026, 9, 16),
    ]


def test_weekly_interval_counts_from_anchor():
    r = rule(frequency="weekly", interval=2, weekdays=[0])
    # anchor Monday 2026-09-07 -> every other Monday
    occ = series_occurrences(r, date(2026, 9, 7), date(2026, 9, 7), date(2026, 10, 6))
    assert [d for d, _, _ in occ] == [date(2026, 9, 7), date(2026, 9, 21), date(2026, 10, 5)]


def test_monthly_day_31_skips_short_months():
    r = rule(frequency="monthly", day_of_month=31)
    occ = series_occurrences(r, date(2026, 1, 1), date(2026, 1, 1), date(2026, 7, 1))
    assert [d for d, _, _ in occ] == [date(2026, 1, 31), date(2026, 3, 31), date(2026, 5, 31)]


def test_range_bounds():
    r = rule(frequency="daily", interval=1)
    # start inclusive, end exclusive
    occ = series_occurrences(r, date(2026, 9, 1), date(2026, 9, 5), date(2026, 9, 8))
    assert [d for d, _, _ in occ] == [date(2026, 9, 5), date(2026, 9, 6), date(2026, 9, 7)]


def test_anchor_after_range_gives_nothing():
    r = rule(frequency="daily", interval=1)
    assert series_occurrences(r, date(2026, 9, 10), date(2026, 9, 1), date(2026, 9, 8)) == []


def test_times_attached():
    r = rule(frequency="daily", start_time="09:30", end_time="11:00")
    occ = series_occurrences(r, date(2026, 9, 1), date(2026, 9, 1), date(2026, 9, 2))
    assert len(occ) == 1
    _, starts, ends = occ[0]
    assert starts.hour == 9 and starts.minute == 30
    assert ends.hour == 11 and ends.minute == 0


def test_first_occurrence_date():
    weekly = rule(frequency="weekly", weekdays=[0])
    monthly = rule(frequency="monthly", day_of_month=31)
    daily = rule(frequency="daily")
    assert first_occurrence_date(weekly, date(2026, 9, 8)) == date(2026, 9, 14)
    assert first_occurrence_date(monthly, date(2026, 2, 1)) == date(2026, 3, 31)
    assert first_occurrence_date(daily, date(2026, 9, 8)) == date(2026, 9, 8)
