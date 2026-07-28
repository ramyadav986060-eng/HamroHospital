from django.contrib import admin
from insurance.models import InsuranceClaim


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_number', 'patient', 'insurance_company', 'amount_claimed', 'status', 'submitted_at')
    list_filter = ('status', 'insurance_company', 'is_cashless')
    search_fields = ('claim_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('claim_number', 'submitted_by', 'reviewed_by', 'submitted_at', 'reviewed_at', 'barcode')

    def save_model(self, request, obj, form, change):
        if not obj.submitted_by_id:
            obj.submitted_by = request.user
        if obj.status != obj.Status.PENDING and not obj.reviewed_by_id:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
