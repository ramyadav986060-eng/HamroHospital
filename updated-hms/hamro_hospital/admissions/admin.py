from django.contrib import admin
from admissions.models import Ward, Bed, Admission, DischargeChecklist, AdmissionDeposit, BedTransfer


class BedInline(admin.TabularInline):
    model = Bed
    extra = 1


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'ward_type', 'total_beds', 'available_beds', 'is_active')
    list_filter = ('ward_type', 'is_active')
    inlines = [BedInline]


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('ward', 'bed_number', 'is_occupied')
    list_filter = ('ward', 'is_occupied')


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ('admission_number', 'patient', 'ward', 'bed', 'status', 'admission_date', 'discharge_date')
    list_filter = ('status', 'ward', 'discharge_condition')
    search_fields = ('admission_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('admission_number', 'created_by', 'barcode')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DischargeChecklist)
class DischargeChecklistAdmin(admin.ModelAdmin):
    list_display = ('admission', 'all_bills_paid', 'nursing_clearance', 'insurance_clearance', 'bed_release_ready', 'updated_at')
    list_filter = ('all_bills_paid', 'nursing_clearance', 'insurance_clearance', 'bed_release_ready')
    search_fields = ('admission__admission_number', 'admission__patient__patient_code')
    readonly_fields = ('updated_at',)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AdmissionDeposit)
class AdmissionDepositAdmin(admin.ModelAdmin):
    list_display = ('admission', 'deposit_type', 'amount', 'payment_method', 'received_by', 'created_at')
    list_filter = ('deposit_type', 'payment_method', 'created_at')
    search_fields = ('admission__admission_number', 'admission__patient__patient_code', 'receipt_number')

    def save_model(self, request, obj, form, change):
        if not obj.received_by_id:
            obj.received_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BedTransfer)
class BedTransferAdmin(admin.ModelAdmin):
    list_display = ('admission', 'from_ward', 'from_bed', 'to_ward', 'to_bed', 'transferred_by', 'transferred_at')
    list_filter = ('to_ward', 'transferred_at')
    search_fields = ('admission__admission_number', 'admission__patient__patient_code', 'reason')
    readonly_fields = ('from_ward', 'from_bed', 'transferred_by', 'transferred_at')

    def save_model(self, request, obj, form, change):
        if not obj.transferred_by_id:
            obj.transferred_by = request.user
        super().save_model(request, obj, form, change)
