from django.conf import settings
from django.db import models


class NursingNote(models.Model):
    """
    One nursing entry against an admission: either a vitals reading, a
    general/shift-handover note, or a medication-administration record.
    Several notes accumulate per admission over the patient's stay.
    """
    class NoteType(models.TextChoices):
        VITALS = 'vitals', 'Vitals Reading'
        GENERAL = 'general', 'General Note'
        PROGRESS = 'progress', 'Progress Note'
        OBSERVATION = 'observation', 'Observation Note'
        MEDICATION = 'medication', 'Medication Administration'
        SHIFT_HANDOVER = 'shift_handover', 'Shift Handover'

    admission = models.ForeignKey(
        'admissions.Admission', on_delete=models.CASCADE, related_name='nursing_notes',
    )
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.GENERAL)
    content = models.TextField(blank=True)

    # Vitals (blank unless note_type == VITALS, but kept available on every
    # note so a quick vitals check can ride along with any entry)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_bpm = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True, help_text='e.g. 120/80')
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    spo2_percent = models.PositiveIntegerField(null=True, blank=True)

    medication_given = models.CharField(max_length=200, blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='nursing_notes',
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nursing_note'
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.get_note_type_display()} - {self.admission.patient.full_name} ({self.recorded_at:%Y-%m-%d %H:%M})"
