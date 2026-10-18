"""Tests for deadline_calculator.py — deterministic deadline computation."""

import sys; sys.path.insert(0, 'src')

import pytest
from datetime import datetime, date
from core.deadline_calculator import (
    compute_deadline, _is_business_day, _add_business_days,
    compute_regulation_deadline, next_business_day,
    US_FEDERAL_HOLIDAYS_2026,
)


class TestClockHours:
    """GDPR-style: clock hours from awareness."""

    def test_72h_from_friday(self):
        """72 clock hours from Friday 14:30 UTC = Monday 14:30 UTC (crosses weekend)."""
        trigger = datetime(2026, 10, 16, 14, 30)  # Friday
        result = compute_deadline(trigger, 72, 'clock_hours')
        assert result == datetime(2026, 10, 19, 14, 30)  # Monday
        assert result.strftime('%A') == 'Monday'

    def test_48h_from_friday(self):
        """48 clock hours from Friday 14:30 UTC = Sunday 14:30 UTC."""
        trigger = datetime(2026, 10, 16, 14, 30)  # Friday
        result = compute_deadline(trigger, 48, 'clock_hours')
        assert result == datetime(2026, 10, 18, 14, 30)  # Sunday

    def test_24h_same_day(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        result = compute_deadline(trigger, 24, 'clock_hours')
        assert result == datetime(2026, 10, 17, 14, 30)

    def test_zero_amount(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        result = compute_deadline(trigger, 0, 'clock_hours')
        assert result == trigger


class TestCalendarDays:
    """CCPA-style: calendar days from discovery."""

    def test_30_days(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        result = compute_deadline(trigger, 30, 'calendar_days')
        assert result == datetime(2026, 11, 15, 14, 30)  # Oct 16 + 30 days = Nov 15

    def test_preserves_time(self):
        trigger = datetime(2026, 10, 16, 9, 0)
        result = compute_deadline(trigger, 1, 'calendar_days')
        assert result.hour == 9
        assert result.minute == 0


class TestBusinessDays:
    """SEC-style: business days, skipping weekends and holidays."""

    def test_1_business_day_from_friday(self):
        """1 business day from Friday = Monday (skips weekend)."""
        trigger = datetime(2026, 10, 16, 14, 30)  # Friday
        result = compute_deadline(trigger, 1, 'business_days')
        assert result.strftime('%A') == 'Monday'
        assert result == datetime(2026, 10, 19, 14, 30)  # Mon Oct 19

    def test_4_business_days_from_friday(self):
        """4 business days from Friday Oct 16 = Thursday Oct 22."""
        trigger = datetime(2026, 10, 16, 14, 30)  # Friday
        result = compute_deadline(trigger, 4, 'business_days')
        # Fri -> Mon(1), Tue(2), Wed(3), Thu(4) = Oct 22
        assert result == datetime(2026, 10, 22, 14, 30)
        assert result.strftime('%A') == 'Thursday'

    def test_skips_holidays(self):
        """Business day calculation skips Thanksgiving (Nov 26, 2026)."""
        trigger = datetime(2026, 11, 25, 14, 30)  # Wednesday before Thanksgiving
        result = compute_deadline(trigger, 2, 'business_days')
        # Wed -> Thu(1), Fri(2) — but Thanksgiving is Nov 26 (Thursday!)
        # Actually Nov 26 2026 is Thanksgiving. So Wed -> Thu(holiday, skip), Fri(1), Mon(2)
        # Wait, let me check: Nov 25 is Wednesday. +1 = Thu Nov 26 (Thanksgiving, skip).
        # +1 = Fri Nov 27 (business day #1). +1 = Mon Nov 30 (business day #2).
        assert result.strftime('%A') == 'Monday'
        assert result.date() == date(2026, 11, 30)


class TestIsBusinessDay:
    """Verify _is_business_day correctly identifies weekends and holidays."""

    def test_weekday(self):
        assert _is_business_day(datetime(2026, 10, 16, 10, 0)) is True  # Friday

    def test_saturday(self):
        assert _is_business_day(datetime(2026, 10, 17, 10, 0)) is False  # Saturday

    def test_sunday(self):
        assert _is_business_day(datetime(2026, 10, 18, 10, 0)) is False  # Sunday

    def test_holiday(self):
        """Thanksgiving 2026 is Nov 26 (Thursday)."""
        assert _is_business_day(datetime(2026, 11, 26, 10, 0)) is False

    def test_non_holiday_thursday(self):
        assert _is_business_day(datetime(2026, 10, 22, 10, 0)) is True


class TestHolidayList:
    """Verify the holiday list uses DATE objects (not datetime)."""

    def test_holidays_are_dates(self):
        """All entries must be date objects for comparison to work."""
        for holiday in US_FEDERAL_HOLIDAYS_2026:
            assert isinstance(holiday, date), f"{holiday} is {type(holiday)}, expected date"

    def test_holidays_match_dt_date(self):
        """dt.date() from a datetime on a holiday should match."""
        thanksgiving = datetime(2026, 11, 26, 12, 0)
        assert thanksgiving.date() in US_FEDERAL_HOLIDAYS_2026


class TestRegulationDeadlines:
    """Named regulation templates."""

    def test_gdpr_art33(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        result = compute_regulation_deadline('GDPR_ART33', trigger)
        assert result == datetime(2026, 10, 19, 14, 30)  # 72h = Monday

    def test_ccpa_breach(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        result = compute_regulation_deadline('CCPA_BREACH', trigger)
        assert result == datetime(2026, 11, 15, 14, 30)  # 30 calendar days from Oct 16 = Nov 15

    def test_unknown_regulation_raises(self):
        trigger = datetime(2026, 10, 16, 14, 30)
        with pytest.raises(ValueError, match="Unknown regulation"):
            compute_regulation_deadline('INVALID_REG', trigger)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
