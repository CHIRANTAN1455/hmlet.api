from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class Property(TimeStampedModel):
    """A building or site that contains one or more rentable units."""

    name = models.CharField(max_length=255, db_index=True)
    address = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties_created",
        # SET_NULL rather than CASCADE: deactivating a staff member must never
        # delete the portfolio they happened to enter.
    )

    class Meta:
        db_table = "properties"
        ordering = ["-created_at"]
        verbose_name_plural = "properties"

    def __str__(self):
        return self.name


class UnitStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    OCCUPIED = "occupied", "Occupied"


class Unit(TimeStampedModel):
    """An individually rentable space within a Property.

    ``status`` is derived, never set directly by a client: a unit is OCCUPIED
    exactly when a contract covers today. It is stored rather than computed per
    request so it can be filtered and indexed in SQL, and is recalculated by the
    contract service on every write. See README > Unit status is derived.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="units",
        # CASCADE is correct here: a unit has no meaning without its building.
    )
    unit_number = models.CharField(max_length=50)
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Default rent for contracts on this unit. Decimal, never float.",
    )
    status = models.CharField(
        max_length=20,
        choices=UnitStatus.choices,
        default=UnitStatus.AVAILABLE,
        db_index=True,
    )

    class Meta:
        db_table = "units"
        ordering = ["property_id", "unit_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "unit_number"],
                name="unique_unit_number_per_property",
            ),
            models.CheckConstraint(
                condition=models.Q(monthly_rent__gte=0),
                name="unit_monthly_rent_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.unit_number}"

    # NB: the `property` FK above shadows Python's `property` builtin inside this
    # class body, so @property decorators cannot be used here. Field name kept
    # because the API contract is /properties/{property_id}/units.
    def is_occupied(self):
        return self.status == UnitStatus.OCCUPIED
