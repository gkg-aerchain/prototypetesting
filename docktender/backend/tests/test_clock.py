"""Docking-clock engine: 36-month rule, window lead, drivers, severity, month math."""
from datetime import date

from app.engines.clock import add_months, docking_window


def test_add_months_basic():
    assert add_months(date(2023, 11, 14), 36) == date(2026, 11, 14)
    assert add_months(date(2024, 1, 15), 1) == date(2024, 2, 15)


def test_add_months_clamps_day():
    # 31 Jan + 1 month -> 29 Feb (2024 is a leap year)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    # 31 Jan + 1 month -> 28 Feb (2023 not leap)
    assert add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)
    # 31 Mar + 1 month -> 30 Apr
    assert add_months(date(2024, 3, 31), 1) == date(2024, 4, 30)


def test_hard_stop_and_days_left():
    # Kalymnos Voyager: last docked 14 Nov 2023, today 3 Jul 2026 -> 134 days left.
    w = docking_window(
        last_docking_date=date(2023, 11, 14),
        special_survey_no=2, uwild_ok=True,
        today=date(2026, 7, 3),
    )
    assert w.hard_stop == date(2026, 11, 14)
    assert w.days_left == 134
    assert w.window_start == date(2026, 7, 17)  # hard_stop - 120 days
    assert w.driver == "SS No. 2"
    assert w.severity == "signal"  # 134 <= 180


def test_uwild_lapse_driver():
    w = docking_window(
        last_docking_date=date(2024, 3, 2),
        special_survey_no=2, uwild_ok=False,
        today=date(2026, 7, 3),
    )
    assert w.driver == "IS + UWILD lapse"


def test_severity_steel_when_far():
    w = docking_window(
        last_docking_date=date(2024, 6, 19),
        special_survey_no=4, uwild_ok=True,
        today=date(2026, 7, 3),
    )
    assert w.hard_stop == date(2027, 6, 19)
    assert w.days_left == 351
    assert w.severity == "steel"


def test_edd_note():
    w = docking_window(
        last_docking_date=date(2024, 1, 1), uwild_ok=True, edd_enrolled=True,
        today=date(2026, 7, 3),
    )
    assert w.edd_note and "EDD" in w.edd_note
    w2 = docking_window(last_docking_date=date(2024, 1, 1), uwild_ok=True, today=date(2026, 7, 3))
    assert w2.edd_note is None


def test_missing_last_docking():
    w = docking_window(last_docking_date=None, today=date(2026, 7, 3))
    assert w.hard_stop is None and w.days_left is None and w.driver == "unknown"
