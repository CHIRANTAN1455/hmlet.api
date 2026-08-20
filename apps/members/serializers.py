from rest_framework import serializers

from .models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ["id", "full_name", "email", "phone"]
        read_only_fields = ["id"]

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Full name cannot be blank.")
        return value

    def validate_email(self, value):
        # Normalise before the uniqueness check so casing cannot create two
        # records for the same tenant.
        value = value.strip().lower()
        if Member.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A member with this email already exists.")
        return value


class MemberSummarySerializer(serializers.ModelSerializer):
    """Compact form for nesting inside a contract."""

    class Meta:
        model = Member
        fields = ["id", "full_name", "email"]
