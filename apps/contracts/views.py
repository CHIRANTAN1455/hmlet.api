from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, generics, status
from rest_framework.response import Response

from .filters import ContractFilter
from .models import Contract
from .serializers import ContractCreateSerializer, ContractSerializer
from .services import create_contract


@extend_schema_view(
    get=extend_schema(
        tags=["Contracts"],
        summary="List contracts",
        description=(
            "Paginated list. `?active=true` returns only contracts whose date "
            "range covers today (end date inclusive)."
        ),
        parameters=[
            OpenApiParameter(
                "active",
                bool,
                description="true = only contracts covering today.",
            ),
            OpenApiParameter("unit", int, description="Filter by unit id."),
            OpenApiParameter("member", int, description="Filter by member id."),
            OpenApiParameter("property", int, description="All contracts in a building."),
        ],
    ),
    post=extend_schema(
        tags=["Contracts"],
        summary="Create a contract",
        description=(
            "Assigns a member to a unit for a date range. Monthly rent defaults "
            "to the unit's rent. Total value is calculated server-side. "
            "Overlapping contracts on the same unit are rejected with 409."
        ),
        request=ContractCreateSerializer,
        responses={201: ContractSerializer},
        examples=[
            OpenApiExample(
                "Twelve month tenancy",
                value={
                    "member_id": 1,
                    "unit_id": 1,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                },
                request_only=True,
            ),
        ],
    ),
)
class ContractListCreateView(generics.ListCreateAPIView):
    filterset_class = ContractFilter
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ["start_date", "end_date", "total_value", "created_at"]
    ordering = ["-start_date"]

    def get_queryset(self):
        # One query for the page regardless of size: member, unit and the
        # unit's property are all joined rather than lazily fetched per row.
        return Contract.objects.select_related("member", "unit", "unit__property")

    def get_serializer_class(self):
        return ContractCreateSerializer if self.request.method == "POST" else ContractSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Business logic lives in the service, not here. The view's only job is
        # to translate HTTP to a call and back.
        contract = create_contract(**serializer.validated_data)

        contract = Contract.objects.select_related(
            "member", "unit", "unit__property"
        ).get(pk=contract.pk)
        return Response(
            ContractSerializer(contract).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Contracts"],
    summary="Retrieve a contract",
)
class ContractDetailView(generics.RetrieveAPIView):
    serializer_class = ContractSerializer
    lookup_url_kwarg = "contract_id"

    def get_queryset(self):
        return Contract.objects.select_related("member", "unit", "unit__property")
