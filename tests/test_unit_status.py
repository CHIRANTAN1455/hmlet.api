"""Unit availability.

Status is a cache of "does a contract cover this date", not an independent
field. These tests pin that relationship, including the case the
sync_unit_statuses command exists for: a unit that should free itself as the
calendar moves, with no request touching the database.
"""

from datetime import timedelta

import pytest

from apps.contracts.services import create_contract, sync_all_unit_statuses
from apps.properties.models import UnitStatus

pytestmark = pytest.mark.django_db


def test_unit_starts_available(unit):
    assert unit.status == UnitStatus.AVAILABLE


def test_current_contract_occupies_the_unit(member, unit, today):
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=10),
        end_date=today + timedelta(days=100),
    )
    unit.refresh_from_db()
    assert unit.status == UnitStatus.OCCUPIED


def test_future_contract_does_not_occupy_the_unit(member, unit, today):
    """A booking that has not started yet leaves the unit available."""
    create_contract(
        member=member,
        unit=unit,
        start_date=today + timedelta(days=30),
        end_date=today + timedelta(days=300),
    )
    unit.refresh_from_db()
    assert unit.status == UnitStatus.AVAILABLE


def test_past_contract_does_not_occupy_the_unit(member, unit, today):
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=300),
        end_date=today - timedelta(days=30),
    )
    unit.refresh_from_db()
    assert unit.status == UnitStatus.AVAILABLE


def test_contract_covers_its_final_day(member, unit, today):
    """End date is inclusive, so the unit is still occupied on that day."""
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=30),
        end_date=today,
    )
    unit.refresh_from_db()
    assert unit.status == UnitStatus.OCCUPIED


def test_sync_frees_a_unit_once_its_contract_has_ended(member, unit, today):
    """The calendar-rollover gap.

    A contract ending yesterday must free its unit today even though nothing
    wrote to the database overnight.
    """
    end = today + timedelta(days=10)
    create_contract(member=member, unit=unit, start_date=today, end_date=end)
    unit.refresh_from_db()
    assert unit.status == UnitStatus.OCCUPIED

    changed = sync_all_unit_statuses(on_date=end + timedelta(days=1))
    unit.refresh_from_db()
    assert changed == 1
    assert unit.status == UnitStatus.AVAILABLE


def test_sync_reoccupies_when_the_next_contract_begins(member, other_member, unit, today):
    create_contract(
        member=member, unit=unit, start_date=today, end_date=today + timedelta(days=10)
    )
    future_start = today + timedelta(days=40)
    create_contract(
        member=other_member,
        unit=unit,
        start_date=future_start,
        end_date=future_start + timedelta(days=100),
    )

    sync_all_unit_statuses(on_date=today + timedelta(days=20))
    unit.refresh_from_db()
    assert unit.status == UnitStatus.AVAILABLE

    sync_all_unit_statuses(on_date=future_start)
    unit.refresh_from_db()
    assert unit.status == UnitStatus.OCCUPIED


def test_sync_is_idempotent(member, unit, today):
    create_contract(
        member=member,
        unit=unit,
        start_date=today - timedelta(days=5),
        end_date=today + timedelta(days=5),
    )
    assert sync_all_unit_statuses() == 0, "nothing should change on a second pass"


def test_status_is_not_writable_through_the_api(auth_client, property_obj):
    """A client must not be able to declare a unit occupied."""
    response = auth_client.post(
        f"/api/properties/{property_obj.id}/units",
        {"unit_number": "09-09", "monthly_rent": "1000.00", "status": "occupied"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == UnitStatus.AVAILABLE
