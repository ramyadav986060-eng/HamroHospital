from django.contrib import admin
from blood_bank.models import BloodUnit, BloodIssue, BloodRequest


@admin.register(BloodUnit)
class BloodUnitAdmin(admin.ModelAdmin):
    list_display = ('bag_number', 'blood_group', 'component', 'status', 'collection_date', 'expiry_date')
    list_filter = ('blood_group', 'component', 'status')
    search_fields = ('bag_number', 'donor_name')
    readonly_fields = ('bag_number', 'added_by')

    def save_model(self, request, obj, form, change):
        if not obj.added_by_id:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('patient', 'blood_group_needed', 'component', 'units_needed', 'urgency', 'status', 'requested_by', 'requested_at')
    list_filter = ('blood_group_needed', 'component', 'urgency', 'status')
    search_fields = ('patient__patient_code', 'patient__first_name', 'patient__last_name', 'clinical_note')
    readonly_fields = ('requested_by', 'requested_at')

    def save_model(self, request, obj, form, change):
        if not obj.requested_by_id:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BloodIssue)
class BloodIssueAdmin(admin.ModelAdmin):
    list_display = ('blood_unit', 'patient', 'issued_by', 'issued_at')
    search_fields = ('blood_unit__bag_number', 'patient__patient_code')
    readonly_fields = ('issued_by', 'issued_at')

    def save_model(self, request, obj, form, change):
        if not obj.issued_by_id:
            obj.issued_by = request.user
        super().save_model(request, obj, form, change)
