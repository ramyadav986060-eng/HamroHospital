from django.contrib import admin
from referrals.models import Referral


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('patient', 'referred_by', 'to_department', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'to_department', 'created_at')
    search_fields = ('patient__patient_code', 'patient__first_name', 'patient__last_name', 'reason')
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
