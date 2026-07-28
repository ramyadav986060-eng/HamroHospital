from django.contrib import admin
from insurance.models import InsuranceClaim


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_number', 'patient', 'insurance_company', 'amount_claimed', 'status', 'submitted_at')
    list_filter = ('status', 'insurance_company', 'is_cashless')
    search_fields = ('claim_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('claim_number',)
