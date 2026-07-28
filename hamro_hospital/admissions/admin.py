from django.contrib import admin
from admissions.models import Ward, Bed, Admission


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
