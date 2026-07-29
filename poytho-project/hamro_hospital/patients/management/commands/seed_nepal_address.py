from django.core.management.base import BaseCommand
from django.db import transaction

from patients.models import Province, District

# Official Nepal federal structure: 7 Provinces, 77 Districts.
NEPAL_PROVINCES_DISTRICTS = {
    1: {
        'name': 'Koshi Province',
        'districts': [
            'Bhojpur', 'Dhankuta', 'Ilam', 'Jhapa', 'Khotang', 'Morang', 'Okhaldhunga',
            'Panchthar', 'Sankhuwasabha', 'Solukhumbu', 'Sunsari', 'Taplejung',
            'Terhathum', 'Udayapur',
        ],
    },
    2: {
        'name': 'Madhesh Province',
        'districts': [
            'Bara', 'Dhanusha', 'Mahottari', 'Parsa', 'Rautahat', 'Saptari',
            'Sarlahi', 'Siraha',
        ],
    },
    3: {
        'name': 'Bagmati Province',
        'districts': [
            'Bhaktapur', 'Chitwan', 'Dhading', 'Dolakha', 'Kathmandu', 'Kavrepalanchok',
            'Lalitpur', 'Makwanpur', 'Nuwakot', 'Ramechhap', 'Rasuwa', 'Sindhuli',
            'Sindhupalchok',
        ],
    },
    4: {
        'name': 'Gandaki Province',
        'districts': [
            'Baglung', 'Gorkha', 'Kaski', 'Lamjung', 'Manang', 'Mustang', 'Myagdi',
            'Nawalpur', 'Parbat', 'Syangja', 'Tanahun',
        ],
    },
    5: {
        'name': 'Lumbini Province',
        'districts': [
            'Arghakhanchi', 'Banke', 'Bardiya', 'Dang', 'Eastern Rukum', 'Gulmi',
            'Kapilvastu', 'Parasi', 'Palpa', 'Pyuthan', 'Rolpa', 'Rupandehi',
        ],
    },
    6: {
        'name': 'Karnali Province',
        'districts': [
            'Dailekh', 'Dolpa', 'Humla', 'Jajarkot', 'Jumla', 'Kalikot', 'Mugu',
            'Salyan', 'Surkhet', 'Western Rukum',
        ],
    },
    7: {
        'name': 'Sudurpashchim Province',
        'districts': [
            'Achham', 'Baitadi', 'Bajhang', 'Bajura', 'Dadeldhura', 'Darchula',
            'Doti', 'Kailali', 'Kanchanpur',
        ],
    },
}


class Command(BaseCommand):
    help = "Seed Nepal's 7 Provinces and 77 Districts (safe to re-run; uses get_or_create)."

    @transaction.atomic
    def handle(self, *args, **options):
        province_count = 0
        district_count = 0

        for number, data in NEPAL_PROVINCES_DISTRICTS.items():
            province, created = Province.objects.get_or_create(
                number=number, defaults={'name': data['name']},
            )
            if created:
                province_count += 1

            for district_name in data['districts']:
                _, created = District.objects.get_or_create(
                    province=province, name=district_name,
                )
                if created:
                    district_count += 1

        total_districts = sum(len(d['districts']) for d in NEPAL_PROVINCES_DISTRICTS.values())
        self.stdout.write(self.style.SUCCESS(
            f"Nepal address data seeded: {province_count} new provinces, "
            f"{district_count} new districts (dataset covers {len(NEPAL_PROVINCES_DISTRICTS)} "
            f"provinces / {total_districts} districts total)."
        ))
