from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class ContractQuerySet(models.QuerySet):
    def active(self, on_date=None):
        """Contracts covering ``on_date`` (default today), end date inclusive.

        This is the single definition of "active" in the system -- the API
        filter, the unit-status calculation and the admin all route through it,
        so they cannot drift apart.
        """
        on_date = on_date or timezone.localdate()
        return self.filter(start_date__lte=on_date, end_date__gte=on_date)

    def expired(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return self.filter(end_date__lt=on_date)

    def upcoming(self, on_date=None):
        on_date = on_date or timezone.localdate()
        return self.filter(start_date__gt=on_date)

    def for_unit(self, unit):
        return self.filter(unit=unit)

    def overlapping(self, unit, start_date, end_date):
        """Contracts on ``unit`` whose date range intersects [start, end].

        Two closed intervals overlap when each starts on or before the other
        ends. Expressed once here so the serializer check and the service check
        cannot disagree.
        """
        return self.filter(
            unit=unit,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )


class Contract(TimeStampedModel):
    """A tenancy: one Member occupying one Unit for a closed date range.

    ``end_date`` is inclusive -- a contract running 2026-01-01 to 2026-12-31
    covers 31 December and is twelve months long.

    ``total_value`` is denormalised rather than computed per request so it can
    be summed and sorted in SQL. It is recalculated by the service layer on
    every write; nothing else may set it.
    """

    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
        related_name="contracts",
        # PROTECT: deleting a tenant who has a tenancy history would destroy
        # the financial record. Force the caller to deal with it explicitly.
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.PROTECT,
        related_name="contracts",
    )

    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Defaults to the unit's rent when omitted on create.",
    )
    total_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Computed: whole months plus a pro-rated remainder. Never client-set.",
    )

    objects = ContractQuerySet.as_manager()

    class Meta:
        db_table = "contracts"
        ordering = ["-start_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="contract_end_date_after_start_date",
            ),
            models.CheckConstraint(
                condition=models.Q(monthly_rent__gt=0),
                name="contract_monthly_rent_positive",
            ),
        ]
        indexes = [
            # Serves both the ?active=true filter and the overlap lookup.
            models.Index(fields=["unit", "start_date", "end_date"], name="contract_unit_range_idx"),
        ]

    def __str__(self):
        return f"{self.member.full_name} @ {self.unit} ({self.start_date} to {self.end_date})"

    @property
    def is_active(self):
        return self.start_date <= timezone.localdate() <= self.end_date

    @property
    def status(self):
        """Derived lifecycle label. Not stored -- it changes with the calendar."""
        today = timezone.localdate()
        if self.start_date > today:
            return "upcoming"
        if self.end_date < today:
            return "expired"
        return "active"
