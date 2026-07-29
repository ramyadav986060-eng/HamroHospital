from django.contrib import admin
from appointments.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_number', 'full_name', 'department', 'doctor', 'preferred_date', 'payment_status', 'registration_fee', 'created_at')
    list_filter = ('payment_status', 'department', 'patient_type')
    search_fields = ('appointment_number', 'first_name', 'last_name', 'phone_number')
    readonly_fields = ('appointment_number', 'transaction_uuid', 'qr_code', 'barcode', 'esewa_ref_id', 'paid_at')
