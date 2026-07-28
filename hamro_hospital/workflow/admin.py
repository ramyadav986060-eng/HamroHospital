from django.contrib import admin
from workflow.models import ServiceOrder, PaymentEvent, PatientTimeline


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'patient', 'service_type', 'status', 'payment_status', 'bill', 'created_at')
    list_filter = ('service_type', 'status', 'payment_status', 'created_at')
    search_fields = ('service_name', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'bill__bill_number')
    readonly_fields = ('total_amount', 'created_at', 'updated_at', 'accepted_at', 'completed_at')


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('bill', 'amount', 'payment_method', 'received_by', 'paid_at')
    list_filter = ('payment_method', 'paid_at')
    search_fields = ('bill__bill_number', 'transaction_reference', 'bill__patient__patient_code')
    readonly_fields = ('created_at',)


@admin.register(PatientTimeline)
class PatientTimelineAdmin(admin.ModelAdmin):
    list_display = ('patient', 'event_type', 'title', 'actor', 'event_at')
    list_filter = ('event_type', 'event_at')
    search_fields = ('patient__patient_code', 'patient__first_name', 'patient__last_name', 'title', 'description')
    readonly_fields = ('created_at',)
