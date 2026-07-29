from django.contrib import admin
from patient_portal.models import PatientAccount


@admin.register(PatientAccount)
class PatientAccountAdmin(admin.ModelAdmin):
    list_display = ('patient', 'is_active', 'created_at', 'last_login_at')
    list_filter = ('is_active',)
    search_fields = ('patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('password_hash', 'created_at', 'last_login_at')
