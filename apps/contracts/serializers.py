from rest_framework import serializers

from apps.members.models import Member
from apps.members.serializers import MemberSummarySerializer
from apps.properties.models import Unit
from apps.properties.serializers import UnitSummarySerializer

from .models import Contract
from .services import contract_duration, find_overlapping_contracts


class ContractSerializer(serializers.ModelSerializer):
    """Read representation. Member and unit are embedded rather than left as
    bare ids -- a contract is meaningless without knowing who and where."""

    member = MemberSummarySerializer(read_only=True)
    unit = UnitSummarySerializer(read_only=True)
    property_id = serializers.IntegerField(source="unit.property_id", read_only=True)
    property_name = serializers.CharField(source="unit.property.name", read_only=True)
    duration_months = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id",
            "member",
            "unit",
            "property_id",
            "property_name",
            "start_date",
            "end_date",
            "monthly_rent",
            "total_value",
            "duration_months",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_duration_months(self, obj):
        months, days = contract_duration(obj.start_date, obj.end_date)
        return {"months": months, "extra_days": days}


class ContractCreateSerializer(serializers.Serializer):
    """Write serializer for POST /api/contracts.

    A plain Serializer rather than a ModelSerializer because total_value is
    derived and must never be accepted from the client -- exposing the model
    directly invites someone to post their own total.
    """

    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(),
        source="member",
    )
    unit_id = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.select_related("property"),
        source="unit",
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    monthly_rent = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Optional. Defaults to the unit's monthly rent.",
    )

    def validate_monthly_rent(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Monthly rent must be greater than zero.")
        return value

    def validate(self, attrs):
        start_date = attrs["start_date"]
        end_date = attrs["end_date"]
        unit = attrs["unit"]

        if end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        # Friendly, specific rejection of a double-booking. This is a
        # convenience, not the guarantee -- the service re-checks under a row
        # lock and the database enforces it with an exclusion constraint.
        conflicts = find_overlapping_contracts(unit, start_date, end_date)
        clash = conflicts.first()
        if clash is not None:
            raise serializers.ValidationError(
                {
                    "unit_id": (
                        f"Unit {unit.unit_number} already has a contract from "
                        f"{clash.start_date} to {clash.end_date} "
                        f"(contract #{clash.id}) overlapping this range."
                    )
                }
            )

        return attrs

    def to_representation(self, instance):
        return ContractSerializer(instance, context=self.context).data


class ContractPreviewSerializer(serializers.Serializer):
    """Response shape for the value-preview helper."""

    monthly_rent = serializers.DecimalField(max_digits=10, decimal_places=2)
    months = serializers.IntegerField()
    extra_days = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
