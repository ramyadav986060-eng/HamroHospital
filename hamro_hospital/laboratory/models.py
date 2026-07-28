# The day-to-day Laboratory workflow still operates on
# consultations.LabTestRequest (a doctor's free-text test request tied to a
# consultation) - see checkpoint documentation, section 4.7.
#
# LabTest below is the *master price/reference catalogue* required by spec
# section 14 (100+ preloaded tests with sample type, price, normal range,
# report format). It is what Cash Counter searches when billing a lab test,
# and what a doctor can optionally pick from when raising a LabTestRequest.
# It is mirrored into website.HospitalService so it appears in the normal
# billing search alongside every other service.
from django.db import models


class LabTest(models.Model):
    class SampleType(models.TextChoices):
        BLOOD = 'blood', 'Blood'
        URINE = 'urine', 'Urine'
        STOOL = 'stool', 'Stool'
        SPUTUM = 'sputum', 'Sputum'
        CSF = 'csf', 'CSF'
        SWAB = 'swab', 'Swab'
        TISSUE = 'tissue', 'Tissue Biopsy'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=150, unique=True)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_tests',
    )
    sample_type = models.CharField(max_length=10, choices=SampleType.choices, default=SampleType.BLOOD)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    normal_range = models.CharField(max_length=200, blank=True, help_text='e.g. "4.0 - 11.0 x10^9/L"')
    report_format = models.CharField(
        max_length=100, blank=True, default='Standard Report',
        help_text='e.g. "Standard Report", "CBC Panel", "Culture & Sensitivity"',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'laboratory_test'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (NPR {self.price})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_hospital_service()

    def _sync_hospital_service(self):
        from website.models import HospitalService
        HospitalService.objects.update_or_create(
            service_code=f"LAB-{self.pk:05d}",
            defaults={
                'name': self.name, 'department': self.department,
                'price': self.price, 'is_active': self.is_active,
            },
        )
