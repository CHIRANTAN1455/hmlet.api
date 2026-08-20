from django.contrib import admin

from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["id", "member", "unit", "start_date", "end_date", "monthly_rent", "total_value", "status"]
    list_filter = ["start_date", "end_date"]
    search_fields = ["member__full_name", "member__email", "unit__unit_number"]
    readonly_fields = ["total_value", "created_at", "updated_at"]
    autocomplete_fields = ["member", "unit"]

    @admin.display(description="Status")
    def status(self, obj):
        return obj.status
