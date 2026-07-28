from django.contrib import admin
from nursing.models import NursingNote


@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    list_display = ('admission', 'note_type', 'recorded_by', 'recorded_at')
    list_filter = ('note_type',)
    search_fields = ('admission__admission_number', 'admission__patient__patient_code')
