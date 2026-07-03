"""Docking-window / 36-month-rule engine.

Hard stop = last_docking_date + 36 months (SOLAS I/10(a)(v) / class 36-month bottom
inspection rule). Intermediate survey inspections may be satisfied by UWILD when the
vessel is UWILD-approved; when not, that drives the window ("IS + UWILD lapse"). EDD
enrolment (IACS Rec 133) is surfaced as an informational flag only. Window opens
120 days before the hard stop (planning convention).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone

WINDOW_LEAD_DAYS = 120
SIGNAL_THRESHOLD_DAYS = 180  # <= this many days left -> the accent 'signal' severity


def add_months(d: date, months: int) -> date:
    """Calendar-month addition, clamping the day to the target month's length."""
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    # clamp day (e.g. 31 Jan + 1 month -> 28/29 Feb)
    if month == 2:
        last = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    elif month in (4, 6, 9, 11):
        last = 30
    else:
        last = 31
    return date(year, month, min(d.day, last))


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


@dataclass
class DockingWindow:
    window_start: date | None
    hard_stop: date | None
    days_left: int | None
    driver: str
    severity: str  # signal|steel  (drives the today/closing accent vs neutral)
    edd_note: str | None

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("window_start", "hard_stop"):
            d[k] = d[k].isoformat() if d[k] else None
        return d


def docking_window(
    *,
    last_docking_date,
    special_survey_no: int = 1,
    uwild_ok: bool = False,
    edd_enrolled: bool = False,
    today: date | None = None,
) -> DockingWindow:
    """Compute the next docking window for a vessel.

    driver is the reason the window exists:
      - "SS No. N"           special survey drives it (the common case)
      - "IS + UWILD lapse"   intermediate survey where UWILD cannot cover it
    """
    today = today or datetime.now(timezone.utc).date()
    last = _as_date(last_docking_date)
    if last is None:
        return DockingWindow(None, None, None, "unknown", "steel", None)

    hard_stop = add_months(last, 36)
    window_start = hard_stop - timedelta(days=WINDOW_LEAD_DAYS)
    days_left = (hard_stop - today).days

    # Driver: an odd special-survey cycle where UWILD is unavailable reads as an
    # intermediate-survey-driven lapse; otherwise the special survey drives it.
    if not uwild_ok:
        driver = "IS + UWILD lapse"
    else:
        driver = f"SS No. {special_survey_no}"

    severity = "signal" if days_left is not None and days_left <= SIGNAL_THRESHOLD_DAYS else "steel"
    edd_note = (
        "EDD enrolled (IACS Rec 133) — extended dry-docking interval may apply, subject to class"
        if edd_enrolled
        else None
    )
    return DockingWindow(window_start, hard_stop, days_left, driver, severity, edd_note)
