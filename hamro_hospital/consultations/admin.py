from django.contrib import admin
from consultations.models import Consultation, PrescriptionItem, LabTestRequest, RadiologyRequest


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('visit', 'doctor', 'diagnosis', 'created_at')
    search_fields = ('visit__receipt_number', 'visit__patient__patient_code', 'diagnosis')
    inlines = [PrescriptionItemInline]


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'consultation', 'urgency', 'status', 'requested_at')
    list_filter = ('status', 'urgency')
    search_fields = ('test_name', 'consultation__visit__patient__patient_code')


@admin.register(RadiologyRequest)
class RadiologyRequestAdmin(admin.ModelAdmin):
    list_display = ('radiology_number', 'service_type', 'consultation', 'urgency', 'status', 'requested_at')
    list_filter = ('status', 'urgency', 'service_type')
    search_fields = ('radiology_number', 'consultation__visit__patient__patient_code')
