from django.contrib import admin
from blood_bank.models import BloodUnit, BloodIssue


@admin.register(BloodUnit)
class BloodUnitAdmin(admin.ModelAdmin):
    list_display = ('bag_number', 'blood_group', 'component', 'status', 'collection_date', 'expiry_date')
    list_filter = ('blood_group', 'component', 'status')
    search_fields = ('bag_number', 'donor_name')
    readonly_fields = ('bag_number',)


@admin.register(BloodIssue)
class BloodIssueAdmin(admin.ModelAdmin):
    list_display = ('blood_unit', 'patient', 'issued_by', 'issued_at')
    search_fields = ('blood_unit__bag_number', 'patient__patient_code')
