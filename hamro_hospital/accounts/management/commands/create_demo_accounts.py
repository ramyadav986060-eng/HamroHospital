from django.core.management.base import BaseCommand

from accounts.models import Role, User

DEMO_PASSWORD = 'sashi'

# username -> role
DEMO_USERS = {
    'admin': Role.SUPER_ADMIN,
    'registration': Role.REGISTRATION_COUNTER,
    'cashier': Role.CASH_COUNTER,
    'doctor': Role.DOCTOR,
    'pharmacy': Role.PHARMACY,
    'laboratory': Role.LABORATORY,
    'radiology': Role.RADIOLOGY,
    'insurance': Role.INSURANCE,
    'admission': Role.WARD_ADMISSION,
    'nursing': Role.NURSING,
    'operationtheatre': Role.OPERATION_THEATRE,
    'bloodbank': Role.BLOOD_BANK,
    'accounts': Role.ACCOUNTS_DEPT,
    'medicalrecords': Role.MEDICAL_RECORDS,
}


class Command(BaseCommand):
    help = (
        'Creates one demo staff login per role (idempotent - safe to re-run). '
        f'All demo accounts share the password: {DEMO_PASSWORD}'
    )

    def handle(self, *args, **options):
        for username, role in DEMO_USERS.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': username.capitalize(),
                    'last_name': 'Demo',
                    'role': role,
                    'is_staff': True,
                    'is_superuser': (role == Role.SUPER_ADMIN),
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.role = role
            user.is_staff = True
            if role == Role.SUPER_ADMIN:
                user.is_superuser = True
            user.save()
            state = 'created' if created else 'updated'
            self.stdout.write(self.style.SUCCESS(f'{state}: {username} ({role})'))

        self.stdout.write(self.style.SUCCESS(f'\nDone. Password for all demo accounts: {DEMO_PASSWORD}'))
