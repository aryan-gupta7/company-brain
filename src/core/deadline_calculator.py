"""Deterministic deadline computation for Company Brain.

No LLM involvement. Pure arithmetic with a business-day calendar.

Deadlines use a typed structure:
  {amount, unit, trigger}
  - amount: int (number of units)
  - unit: 'clock_hours' | 'calendar_days' | 'business_days'
  - trigger: 'detection' | 'awareness' | 'discovery'

Holiday comparison uses DATE objects, not datetime objects.
(Previous bug: datetime objects were compared against dates — never matched.)
"""

from datetime import datetime, timedelta, date
from typing import Literal

Unit = Literal['clock_hours', 'calendar_days', 'business_days']
Trigger = Literal['detection', 'awareness', 'discovery']

# US Federal Holidays 2026 — stored as DATE objects for correct comparison
US_FEDERAL_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 10, 12), # Columbus Day
    date(2026, 11, 11), # Veterans Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas Day
}

# Indian National Holidays 2026 — stored as DATE objects
# (Used for India-specific business-day computations)
INDIAN_HOLIDAYS_2026 = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 14),  # Holi (approx)
    date(2026, 3, 26),  # Ram Navami (approx)
    date(2026, 4, 3),   # Mahavir Jayanti
    date(2026, 4, 10),  # Good Friday
    date(2026, 4, 14),  # Ambedkar Jayanti
    date(2026, 5, 1),   # May Day
    date(2026, 6, 26),  # Eid al-Adha (approx)
    date(2026, 8, 15),  # Independence Day
    date(2026, 9, 18),  # Ganesh Chaturthi (approx)
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 20),  # Diwali (approx)
    date(2026, 11, 4),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
}


def compute_deadline(
    trigger_at: datetime,
    amount: int,
    unit: Unit,
) -> datetime:
    """Compute deadline from a trigger time.

    Args:
        trigger_at: When the triggering event occurred.
        amount: Number of units until deadline.
        unit: 'clock_hours' (GDPR), 'calendar_days' (CCPA),
              or 'business_days' (SEC).

    Returns:
        The deadline datetime.

    Raises:
        ValueError: If unit is unknown.
    """
    if amount == 0:
        return trigger_at

    if unit == 'clock_hours':
        return trigger_at + timedelta(hours=amount)
    elif unit == 'calendar_days':
        return trigger_at + timedelta(days=amount)
    elif unit == 'business_days':
        return _add_business_days(trigger_at, amount)
    else:
        raise ValueError(f"Unknown unit: {unit!r}")


def _add_business_days(start: datetime, days: int) -> datetime:
    """Add business days, skipping weekends and US federal holidays."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if _is_business_day(current):
            added += 1
    # Preserve time-of-day from the trigger
    return current.replace(hour=start.hour, minute=start.minute, second=start.second)


def _is_business_day(dt: datetime) -> bool:
    """Check if a datetime falls on a business day.

    Uses .date() for holiday comparison (not datetime directly).
    """
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if dt.date() in US_FEDERAL_HOLIDAYS_2026:
        return False
    return True


def next_business_day(dt: datetime) -> datetime:
    """Return the next business day after dt (same time-of-day)."""
    current = dt
    while True:
        current += timedelta(days=1)
        if _is_business_day(current):
            return current.replace(hour=dt.hour, minute=dt.minute, second=dt.second)


# --- Pre-defined deadline templates for common regulations ---

GDPR_ART33 = {'amount': 72, 'unit': 'clock_hours', 'trigger': 'awareness'}
GDPR_ART34 = {'amount': 48, 'unit': 'clock_hours', 'trigger': 'awareness'}
CCPA_BREACH = {'amount': 30, 'unit': 'calendar_days', 'trigger': 'discovery'}
CCPA_AG_NOTIFY = {'amount': 15, 'unit': 'calendar_days', 'trigger': 'discovery'}
HIPAA_INDIVIDUAL = {'amount': 60, 'unit': 'calendar_days', 'trigger': 'discovery'}
HIPAA_HHS_500PLUS = {'amount': 60, 'unit': 'calendar_days', 'trigger': 'discovery'}
SEC_8K_105 = {'amount': 4, 'unit': 'business_days', 'trigger': 'awareness'}

# --- India regulations ---
# CERT-In April 2022 Directive: 6-hour breach reporting for high-severity incidents
# DPDPA 2023: Data Protection Board notification (Section 8(6)) — timeline per rules
# IT Act Section 72A: Disclosure in breach of contract
CERT_IN_BREACH = {'amount': 6, 'unit': 'clock_hours', 'trigger': 'detection'}
DPDPA_BREACH = {'amount': 72, 'unit': 'clock_hours', 'trigger': 'awareness'}
# Note: DPDPA 2023 phased commencement — core Nov 2025, penalties Nov 2026, rest May 2027
# CERT-In 6h rule applies to high-severity incidents only (per FAQ clarification)


def compute_regulation_deadline(
    regulation: str,
    trigger_at: datetime,
) -> datetime:
    """Compute deadline for a named regulation."""
    templates = {
        'GDPR_ART33': GDPR_ART33,
        'GDPR_ART34': GDPR_ART34,
        'CCPA_BREACH': CCPA_BREACH,
        'CCPA_AG_NOTIFY': CCPA_AG_NOTIFY,
        'HIPAA_INDIVIDUAL': HIPAA_INDIVIDUAL,
        'HIPAA_HHS_500PLUS': HIPAA_HHS_500PLUS,
        'SEC_8K_105': SEC_8K_105,
        'CERT_IN_BREACH': CERT_IN_BREACH,
        'DPDPA_BREACH': DPDPA_BREACH,
    }
    if regulation not in templates:
        raise ValueError(f"Unknown regulation: {regulation!r}. Available: {list(templates.keys())}")
    t = templates[regulation]
    return compute_deadline(trigger_at, t['amount'], t['unit'])
