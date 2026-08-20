from rest_framework import serializers

from .models import Property, Unit


class UnitSerializer(serializers.ModelSerializer):
    """Read representation of a unit, including its parent property inline."""

    property_id = serializers.IntegerField(source="property.id", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Unit
        fields = [
            "id",
            "property_id",
            "property_name",
            "unit_number",
            "monthly_rent",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class UnitCreateSerializer(serializers.ModelSerializer):
    """Write serializer for POST /api/properties/{property_id}/units.

    ``property`` is taken from the URL, not the body, so a caller cannot create
    a unit under a different property than the one they addressed. ``status`` is
    likewise absent: it is derived from contracts, never client-supplied.
    """

    class Meta:
        model = Unit
        fields = ["id", "unit_number", "monthly_rent"]
        read_only_fields = ["id"]

    def validate_unit_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Unit number cannot be blank.")
        return value

    def validate_monthly_rent(self, value):
        if value <= 0:
            raise serializers.ValidationError("Monthly rent must be greater than zero.")
        return value

    def validate(self, attrs):
        # The parent property is injected by the view from the URL kwarg.
        parent = self.context["property"]
        unit_number = attrs.get("unit_number")
        if Unit.objects.filter(property=parent, unit_number__iexact=unit_number).exists():
            raise serializers.ValidationError(
                {
                    "unit_number": (
                        f"Unit '{unit_number}' already exists in property "
                        f"'{parent.name}'."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data["property"] = self.context["property"]
        return super().create(validated_data)


class UnitSummarySerializer(serializers.ModelSerializer):
    """Compact unit representation for nesting inside a property."""

    class Meta:
        model = Unit
        fields = ["id", "unit_number", "monthly_rent", "status"]


class PropertySerializer(serializers.ModelSerializer):
    """List representation: counts rather than the full unit collection."""

    unit_count = serializers.IntegerField(read_only=True)
    available_unit_count = serializers.IntegerField(read_only=True)
    created_by = serializers.EmailField(source="created_by.email", read_only=True, default=None)

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "address",
            "unit_count",
            "available_unit_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class PropertyDetailSerializer(PropertySerializer):
    """Detail representation: the full unit list is included.

    Split from the list serializer deliberately -- embedding every unit in a
    list response would make the payload grow with the portfolio.
    """

    units = UnitSummarySerializer(many=True, read_only=True)

    class Meta(PropertySerializer.Meta):
        fields = PropertySerializer.Meta.fields + ["units"]


class PropertyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ["id", "name", "address"]
        read_only_fields = ["id"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_address(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Address cannot be blank.")
        return value
