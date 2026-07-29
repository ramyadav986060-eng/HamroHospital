from django.contrib import admin
from nursing.models import NursingNote


@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    list_display = ('admission', 'note_type', 'recorded_by', 'recorded_at')
    list_filter = ('note_type',)
    search_fields = ('admission__admission_number', 'admission__patient__patient_code')
    readonly_fields = ('recorded_by', 'recorded_at')

    def save_model(self, request, obj, form, change):
        if not obj.recorded_by_id:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
