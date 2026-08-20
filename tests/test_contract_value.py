"""Total contract value.

Pure functions, so no database. These encode the rounding and pro-rata rules
documented in README > Total contract value -- if someone changes the
convention, these fail and force the README to be updated with it.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.contracts.services import calculate_total_value, contract_duration


@pytest.mark.parametrize(
    "start,end,rent,expected,reason",
    [
        # End date is inclusive, so a calendar year is exactly 12 months.
        (date(2026, 1, 1), date(2026, 12, 31), "1000", "12000.00", "full year"),
        (date(2026, 1, 1), date(2026, 6, 30), "1000", "6000.00", "half year"),
        # Mid-month to the day before the same day-of-month six months on.
        (date(2026, 1, 15), date(2026, 7, 14), "1000", "6000.00", "six months mid-month"),
        (date(2026, 1, 1), date(2027, 6, 30), "1500", "27000.00", "eighteen months"),
        # Partial months are pro-rated by the length of the month they fall in.
        (date(2026, 1, 1), date(2026, 1, 15), "1000", "483.87", "15 days in a 31-day month"),
        (date(2026, 2, 1), date(2026, 2, 15), "1000", "535.71", "15 days in a 28-day month"),
        (date(2026, 4, 1), date(2026, 4, 15), "1000", "500.00", "15 days in a 30-day month"),
        (date(2026, 1, 1), date(2026, 1, 1), "1000", "32.26", "single day"),
        (date(2026, 3, 1), date(2026, 4, 5), "900", "1050.00", "one month plus five days"),
        # February in a leap year is still one whole month.
        (date(2024, 2, 1), date(2024, 2, 29), "1000", "1000.00", "leap february"),
        (date(2023, 2, 1), date(2023, 2, 28), "1000", "1000.00", "non-leap february"),
        # Rounding lands on a half cent and must round up, not down or to even.
        (date(2026, 1, 1), date(2026, 1, 7), "1000", "225.81", "seven days rounds half up"),
    ],
)
def test_total_value(start, end, rent, expected, reason):
    assert calculate_total_value(Decimal(rent), start, end) == Decimal(expected), reason


@pytest.mark.parametrize(
    "start,end,months,days",
    [
        (date(2026, 1, 1), date(2026, 12, 31), 12, 0),
        (date(2026, 1, 1), date(2026, 1, 15), 0, 15),
        (date(2026, 3, 1), date(2026, 4, 5), 1, 5),
        (date(2026, 1, 1), date(2026, 1, 1), 0, 1),
    ],
)
def test_duration_split(start, end, months, days):
    assert contract_duration(start, end) == (months, days)


def test_value_is_decimal_not_float():
    """Money must never round-trip through a float."""
    result = calculate_total_value(Decimal("1000.00"), date(2026, 1, 1), date(2026, 1, 15))
    assert isinstance(result, Decimal)


def test_value_always_two_decimal_places():
    result = calculate_total_value(Decimal("999.99"), date(2026, 1, 1), date(2026, 1, 10))
    assert result.as_tuple().exponent == -2


def test_longer_contract_is_never_cheaper():
    """Monotonicity: extending the end date cannot reduce the total."""
    rent = Decimal("1200.00")
    start = date(2026, 1, 1)
    previous = Decimal("0")
    for end_day in [date(2026, 1, 5), date(2026, 2, 1), date(2026, 6, 30), date(2027, 1, 1)]:
        current = calculate_total_value(rent, start, end_day)
        assert current > previous
        previous = current
