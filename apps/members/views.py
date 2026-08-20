from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics

from .models import Member
from .serializers import MemberCreateSerializer, MemberSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["Members"],
        summary="List members",
        description="Paginated list of tenants. Supports ?search= on name and email.",
    ),
    post=extend_schema(
        tags=["Members"],
        summary="Create a member",
        request=MemberCreateSerializer,
        responses={201: MemberSerializer},
    ),
)
class MemberListCreateView(generics.ListCreateAPIView):
    queryset = Member.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email"]
    ordering_fields = ["full_name", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return MemberCreateSerializer if self.request.method == "POST" else MemberSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        instance = Member.objects.get(pk=response.data["id"])
        response.data = MemberSerializer(instance).data
        return response
