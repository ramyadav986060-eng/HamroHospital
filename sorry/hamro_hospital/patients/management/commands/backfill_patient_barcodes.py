from django.core.management.base import BaseCommand

from patients.models import Patient


class Command(BaseCommand):
    help = "Generate a Code128 barcode for any existing patients that don't have one yet."

    def handle(self, *args, **options):
        patients = Patient.objects.filter(barcode='') | Patient.objects.filter(barcode__isnull=True)
        count = 0
        for patient in patients.distinct():
            patient._generate_barcode()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Generated barcodes for {count} patient(s)."))
