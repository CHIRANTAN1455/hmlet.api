from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, generics

from .filters import UnitFilter
from .models import Property, Unit, UnitStatus
from .serializers import (
    PropertyCreateSerializer,
    PropertyDetailSerializer,
    PropertySerializer,
    UnitCreateSerializer,
    UnitSerializer,
)


def _property_queryset():
    """Properties annotated with unit counts.

    Annotating in SQL keeps the list endpoint at a constant number of queries
    regardless of how many properties or units exist -- counting in Python would
    be one extra query per row.
    """
    return Property.objects.select_related("created_by").annotate(
        unit_count=Count("units", distinct=True),
        available_unit_count=Count(
            "units",
            filter=Q(units__status=UnitStatus.AVAILABLE),
            distinct=True,
        ),
    )


@extend_schema_view(
    get=extend_schema(
        tags=["Properties"],
        summary="List properties",
        description="Paginated list with unit counts. Supports ?search= on name and address.",
    ),
    post=extend_schema(
        tags=["Properties"],
        summary="Create a property",
        request=PropertyCreateSerializer,
        responses={201: PropertySerializer},
    ),
)
class PropertyListCreateView(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "address"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _property_queryset()

    def get_serializer_class(self):
        return PropertyCreateSerializer if self.request.method == "POST" else PropertySerializer

    def perform_create(self, serializer):
        # Attribution comes from the token, never from the request body.
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Re-serialise through the read serializer so the response carries the
        # annotated counts rather than the bare write fields.
        instance = _property_queryset().get(pk=response.data["id"])
        response.data = PropertySerializer(instance).data
        return response


@extend_schema(
    tags=["Properties"],
    summary="Retrieve a property with its units",
)
class PropertyDetailView(generics.RetrieveAPIView):
    serializer_class = PropertyDetailSerializer
    lookup_url_kwarg = "property_id"

    def get_queryset(self):
        # prefetch_related keeps the nested unit list to one extra query total.
        return _property_queryset().prefetch_related("units")


@extend_schema(
    tags=["Units"],
    summary="Add a unit to a property",
    request=UnitCreateSerializer,
    responses={201: UnitSerializer},
)
class UnitCreateView(generics.CreateAPIView):
    serializer_class = UnitCreateSerializer

    def get_property(self):
        return get_object_or_404(Property, pk=self.kwargs["property_id"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["property"] = self.get_property()
        return context

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = Unit.objects.select_related("property").get(pk=response.data["id"])
        response.data = UnitSerializer(instance).data
        return response


@extend_schema_view(
    get=extend_schema(
        tags=["Units"],
        summary="List units",
        description=(
            "Paginated list across all properties. Filter with ?status=available "
            "or ?status=occupied, and narrow to one building with ?property={id}."
        ),
        parameters=[
            OpenApiParameter(
                "status",
                str,
                description="available | occupied",
                enum=[c[0] for c in UnitStatus.choices],
            ),
            OpenApiParameter("property", int, description="Property id"),
        ],
    )
)
class UnitListView(generics.ListAPIView):
    serializer_class = UnitSerializer
    filterset_class = UnitFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["unit_number", "property__name"]
    ordering_fields = ["monthly_rent", "unit_number", "created_at"]

    def get_queryset(self):
        # select_related avoids one query per unit when serialising property_name.
        return Unit.objects.select_related("property").all()
