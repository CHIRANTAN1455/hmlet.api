import django_filters

from .models import Unit, UnitStatus


class UnitFilter(django_filters.FilterSet):
    """Query-parameter filtering for GET /api/units.

    ``status`` is the one the brief calls for; the rest are cheap additions that
    make the endpoint actually usable for a front end.
    """

    status = django_filters.ChoiceFilter(
        choices=UnitStatus.choices,
        help_text="Filter by availability: available | occupied",
    )
    property = django_filters.NumberFilter(
        field_name="property_id",
        help_text="Only units belonging to this property id.",
    )
    min_rent = django_filters.NumberFilter(
        field_name="monthly_rent",
        lookup_expr="gte",
        help_text="Monthly rent greater than or equal to this amount.",
    )
    max_rent = django_filters.NumberFilter(
        field_name="monthly_rent",
        lookup_expr="lte",
        help_text="Monthly rent less than or equal to this amount.",
    )

    class Meta:
        model = Unit
        fields = ["status", "property", "min_rent", "max_rent"]
