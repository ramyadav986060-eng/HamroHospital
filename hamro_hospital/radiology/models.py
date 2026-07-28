# The day-to-day Radiology workflow still operates on
# consultations.RadiologyRequest (a doctor's request tied to a consultation,
# using a fixed set of common service types) - see checkpoint documentation,
# section 4.8.
#
# RadiologyTest below is the *master price/reference catalogue* required by
# spec section 15 (100+ preloaded imaging services with department, report
# type, and fixed price). It is what Cash Counter searches when billing an
# imaging service, and is mirrored into website.HospitalService so it
# appears in the normal billing search alongside every other service.
from django.db import models


class RadiologyTest(models.Model):
    class ReportType(models.TextChoices):
        IMAGING_REPORT = 'imaging_report', 'Imaging Report'
        SCAN_REPORT = 'scan_report', 'Scan Report'
        DOPPLER_REPORT = 'doppler_report', 'Doppler Report'
        ECG_STRIP = 'ecg_strip', 'ECG Strip'
        ECHO_REPORT = 'echo_report', 'Echo Report'
        DENSITY_REPORT = 'density_report', 'Bone Density Report'

    name = models.CharField(max_length=150, unique=True)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='radiology_tests',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    report_type = models.CharField(max_length=20, choices=ReportType.choices, default=ReportType.IMAGING_REPORT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'radiology_test'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (NPR {self.price})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_hospital_service()

    def _sync_hospital_service(self):
        from website.models import HospitalService
        HospitalService.objects.update_or_create(
            service_code=f"RAD-{self.pk:05d}",
            defaults={
                'name': self.name, 'department': self.department,
                'price': self.price, 'is_active': self.is_active,
            },
        )
