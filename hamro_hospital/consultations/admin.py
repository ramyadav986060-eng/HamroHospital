from django.contrib import admin
from django.utils import timezone
from consultations.models import Consultation, PrescriptionItem, LabTestRequest, RadiologyRequest, RequestStatus


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
    search_fields = ('test_name', 'consultation__visit__patient__patient_code', 'patient__patient_code')
    readonly_fields = ('lab_code', 'barcode', 'requested_at', 'accepted_by', 'accepted_at', 'processed_by', 'completed_at')

    def save_model(self, request, obj, form, change):
        if obj.status in {RequestStatus.ACCEPTED, RequestStatus.SAMPLE_COLLECTED, RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED} and not obj.accepted_by_id:
            obj.accepted_by = request.user
            obj.accepted_at = timezone.now()
        if obj.status == RequestStatus.COMPLETED:
            if not obj.processed_by_id:
                obj.processed_by = request.user
            if not obj.completed_at:
                obj.completed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(RadiologyRequest)
class RadiologyRequestAdmin(admin.ModelAdmin):
    list_display = ('radiology_number', 'service_type', 'consultation', 'urgency', 'status', 'requested_at')
    list_filter = ('status', 'urgency', 'service_type')
    search_fields = ('radiology_number', 'consultation__visit__patient__patient_code', 'patient__patient_code')
    readonly_fields = ('radiology_number', 'barcode', 'requested_at', 'accepted_by', 'accepted_at', 'processed_by', 'completed_at')

    def save_model(self, request, obj, form, change):
        if obj.status in {RequestStatus.ACCEPTED, RequestStatus.SAMPLE_COLLECTED, RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED} and not obj.accepted_by_id:
            obj.accepted_by = request.user
            obj.accepted_at = timezone.now()
        if obj.status == RequestStatus.COMPLETED:
            if not obj.processed_by_id:
                obj.processed_by = request.user
            if not obj.completed_at:
                obj.completed_at = timezone.now()
        super().save_model(request, obj, form, change)
