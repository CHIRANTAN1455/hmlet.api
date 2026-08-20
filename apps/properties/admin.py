from django.contrib import admin

from .models import Property, Unit


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0
    fields = ["unit_number", "monthly_rent", "status"]
    readonly_fields = ["status"]  # derived from contracts


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["name", "address", "unit_count", "created_by", "created_at"]
    search_fields = ["name", "address"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [UnitInline]

    @admin.display(description="Units")
    def unit_count(self, obj):
        return obj.units.count()


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["unit_number", "property", "monthly_rent", "status"]
    list_filter = ["status", "property"]
    search_fields = ["unit_number", "property__name"]
    readonly_fields = ["status", "created_at", "updated_at"]
