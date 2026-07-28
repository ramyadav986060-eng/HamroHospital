from django.contrib import admin
from documents.models import PatientDocument


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'category', 'version', 'is_active', 'uploaded_by', 'uploaded_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('uploaded_at', 'uploaded_by', 'uploaded_by_role', 'deleted_by', 'deleted_at')

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
            obj.uploaded_by_role = getattr(request.user, 'role', '')
        super().save_model(request, obj, form, change)
