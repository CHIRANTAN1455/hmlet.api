"""Contract domain logic.

Everything with a business rule in it lives here rather than in views or
serializers, so it can be exercised without an HTTP request and reused by the
management command and the admin.
"""

from calendar import monthrange
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import Conflict
from apps.properties.models import Unit, UnitStatus

from .models import Contract

TWO_PLACES = Decimal("0.01")


# --- Duration and value ---------------------------------------------------


def contract_duration(start_date, end_date):
    """Split a closed date range into (whole_months, leftover_days).

    ``end_date`` is inclusive, so the arithmetic is done against the day after
    it. That is what makes 2026-01-01 -> 2026-12-31 come out as exactly twelve
    months rather than eleven months and thirty days.
    """
    boundary = end_date + timedelta(days=1)
    delta = relativedelta(boundary, start_date)
    months = delta.years * 12 + delta.months
    return months, delta.days


def calculate_total_value(monthly_rent, start_date, end_date):
    """Total rent owed over the life of the contract.

    Whole months are charged at the full monthly rent. A partial month at the
    end is pro-rated by day, using the length of the calendar month the
    remainder falls in -- so a 15-day tail in January divides by 31, and the
    same tail in February divides by 28.

    Decimal throughout; quantised to 2dp with ROUND_HALF_UP. Money is never a
    float here.
    """
    monthly_rent = Decimal(monthly_rent)
    months, days = contract_duration(start_date, end_date)

    total = monthly_rent * months

    if days:
        # The remainder begins after the whole months have elapsed; its
        # denominator is the length of the month it starts in.
        anchor = start_date + relativedelta(months=months)
        days_in_month = monthrange(anchor.year, anchor.month)[1]
        total += monthly_rent * Decimal(days) / Decimal(days_in_month)

    return total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# --- Overlap ---------------------------------------------------------------


def find_overlapping_contracts(unit, start_date, end_date, exclude_pk=None):
    qs = Contract.objects.overlapping(unit, start_date, end_date).select_related("member")
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


# --- Unit status -----------------------------------------------------------


def recompute_unit_status(unit, on_date=None):
    """Set unit.status from whether any contract covers ``on_date``.

    Status is a cache of a query, not an independent fact. Writing it only when
    it actually changes keeps updated_at meaningful.
    """
    on_date = on_date or timezone.localdate()
    occupied = Contract.objects.for_unit(unit).active(on_date).exists()
    desired = UnitStatus.OCCUPIED if occupied else UnitStatus.AVAILABLE

    if unit.status != desired:
        unit.status = desired
        unit.save(update_fields=["status", "updated_at"])
    return unit


def sync_all_unit_statuses(on_date=None):
    """Recompute every unit's status. Used by the sync_unit_statuses command.

    Needed because status depends on the calendar: a contract that ended
    yesterday frees its unit today without any request touching the database.
    """
    on_date = on_date or timezone.localdate()
    changed = 0
    for unit in Unit.objects.all().iterator():
        before = unit.status
        recompute_unit_status(unit, on_date=on_date)
        if unit.status != before:
            changed += 1
    return changed


# --- Creation --------------------------------------------------------------


@transaction.atomic
def create_contract(*, member, unit, start_date, end_date, monthly_rent=None):
    """Create a contract, rejecting double-bookings and updating unit status.

    Concurrency: the unit row is locked with select_for_update for the duration
    of the transaction, so two simultaneous requests for the same unit are
    serialised rather than both passing the overlap check and both inserting.
    The PostgreSQL exclusion constraint behind this is the actual guarantee --
    see the 0002 migration.
    """
    # Re-fetch under a row lock. Anything read before the lock is stale.
    locked_unit = Unit.objects.select_for_update().select_related("property").get(pk=unit.pk)

    if monthly_rent is None:
        monthly_rent = locked_unit.monthly_rent

    conflicts = find_overlapping_contracts(locked_unit, start_date, end_date)
    if conflicts.exists():
        clash = conflicts.first()
        raise Conflict(
            f"Unit {locked_unit.unit_number} is already booked from "
            f"{clash.start_date} to {clash.end_date} by {clash.member.full_name}. "
            f"Requested range {start_date} to {end_date} overlaps it."
        )

    contract = Contract.objects.create(
        member=member,
        unit=locked_unit,
        start_date=start_date,
        end_date=end_date,
        monthly_rent=monthly_rent,
        total_value=calculate_total_value(monthly_rent, start_date, end_date),
    )

    recompute_unit_status(locked_unit)
    return contract
