import django_filters
from django.utils import timezone

from .models import Contract


class ContractFilter(django_filters.FilterSet):
    """Query-parameter filtering for GET /api/contracts."""

    active = django_filters.BooleanFilter(
        method="filter_active",
        help_text="true = only contracts covering today; false = only those not covering today.",
    )
    unit = django_filters.NumberFilter(field_name="unit_id")
    member = django_filters.NumberFilter(field_name="member_id")
    property = django_filters.NumberFilter(
        field_name="unit__property_id",
        help_text="All contracts across a building.",
    )
    starts_after = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    ends_before = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")

    class Meta:
        model = Contract
        fields = ["active", "unit", "member", "property", "starts_after", "ends_before"]

    def filter_active(self, queryset, name, value):
        # Routed through the queryset method so "active" has exactly one
        # definition shared with unit-status calculation.
        today = timezone.localdate()
        if value:
            return queryset.active(today)
        return queryset.exclude(pk__in=queryset.active(today).values("pk"))
