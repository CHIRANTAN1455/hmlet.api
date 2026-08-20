"""Double-booking prevention.

Three independent layers, tested independently, because each one fails
differently:

  1. serializer  -> a friendly 400 naming the conflict
  2. service     -> a row lock so concurrent creates serialise
  3. database    -> an exclusion constraint that holds even when 1 and 2 are
                    bypassed entirely

A test that only exercised layer 1 would still pass if the constraint were
dropped, which is exactly the regression worth catching.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from apps.common.exceptions import Conflict
from apps.contracts.models import Contract
from apps.contracts.services import create_contract

pytestmark = pytest.mark.django_db


# --- Layer 1 and 2: service-level rejection --------------------------------


@pytest.mark.parametrize(
    "start,end,label",
    [
        (date(2026, 1, 1), date(2026, 12, 31), "identical range"),
        (date(2025, 6, 1), date(2026, 3, 1), "overlaps the start"),
        (date(2026, 10, 1), date(2027, 4, 1), "overlaps the end"),
        (date(2026, 5, 1), date(2026, 6, 1), "entirely inside"),
        (date(2025, 1, 1), date(2027, 1, 1), "entirely surrounds"),
        (date(2026, 12, 31), date(2027, 6, 1), "touches the final day"),
        (date(2025, 6, 1), date(2026, 1, 1), "touches the first day"),
    ],
)
def test_overlapping_contract_is_rejected(member, other_member, unit, start, end, label):
    create_contract(
        member=member,
        unit=unit,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    with pytest.raises(Conflict):
        create_contract(member=other_member, unit=unit, start_date=start, end_date=end)
    assert Contract.objects.filter(unit=unit).count() == 1, label


@pytest.mark.parametrize(
    "start,end,label",
    [
        (date(2027, 1, 1), date(2027, 6, 30), "starts the day after the other ends"),
        (date(2025, 1, 1), date(2025, 12, 31), "ends the day before the other starts"),
    ],
)
def test_adjacent_ranges_are_allowed(member, other_member, unit, start, end, label):
    """Back-to-back tenancies are normal and must not be treated as overlaps."""
    create_contract(
        member=member,
        unit=unit,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    create_contract(member=other_member, unit=unit, start_date=start, end_date=end)
    assert Contract.objects.filter(unit=unit).count() == 2, label


def test_same_dates_on_a_different_unit_are_allowed(member, other_member, unit, other_unit):
    """The constraint is per unit, not global."""
    create_contract(member=member, unit=unit, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    create_contract(
        member=other_member, unit=other_unit, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    assert Contract.objects.count() == 2


def test_conflict_message_identifies_the_clashing_contract(member, other_member, unit):
    create_contract(member=member, unit=unit, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    with pytest.raises(Conflict) as exc:
        create_contract(
            member=other_member, unit=unit, start_date=date(2026, 6, 1), end_date=date(2026, 7, 1)
        )
    detail = str(exc.value.detail)
    assert "2026-01-01" in detail and "2026-12-31" in detail
    assert member.full_name in detail


# --- Layer 3: the database guarantee ---------------------------------------


@pytest.mark.postgres
@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Exclusion constraints are PostgreSQL-only; SQLite falls back to app-level checks.",
)
def test_database_rejects_overlap_even_when_application_checks_are_bypassed(member, other_member, unit):
    """The guarantee, not the convenience.

    Writes straight through the ORM, skipping the serializer and the service.
    If this passes only because of application code, the constraint is missing
    and concurrent requests can double-book.
    """
    create_contract(member=member, unit=unit, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    with pytest.raises(IntegrityError, match="no_overlapping_contracts_per_unit"):
        with transaction.atomic():
            Contract.objects.create(
                member=other_member,
                unit=unit,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 7, 1),
                monthly_rent=Decimal("1000.00"),
                total_value=Decimal("1000.00"),
            )


@pytest.mark.postgres
@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Exclusion constraints are PostgreSQL-only.",
)
def test_exclusion_constraint_exists_with_inclusive_bounds(db):
    """Guards the '[]' bounds specifically.

    With the default '[)' bounds a contract could start on the exact day
    another ends, silently double-booking that day.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'no_overlapping_contracts_per_unit'"
        )
        row = cursor.fetchone()

    assert row is not None, "exclusion constraint is missing"
    definition = row[0]
    assert "EXCLUDE USING gist" in definition
    assert "unit_id WITH =" in definition
    assert "'[]'" in definition, "bounds must be inclusive on both ends"
