import os
from datetime import datetime

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Creates a timestamped JSON backup of the entire database (all apps) '
        'under BASE_DIR/backups/. Restore with: python manage.py restore_data <path>'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir', default=None,
            help='Directory to write the backup into (default: BASE_DIR/backups)',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir'] or os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'tuh_backup_{timestamp}.json')

        with open(filename, 'w', encoding='utf-8') as f:
            management.call_command(
                'dumpdata',
                exclude=['contenttypes', 'auth.permission', 'sessions.session', 'admin.logentry'],
                indent=2,
                stdout=f,
            )

        self.stdout.write(self.style.SUCCESS(f'Backup written to {filename}'))
        self.stdout.write(
            'Note: uploaded files under MEDIA_ROOT (patient photos, lab reports, '
            'documents, etc.) are NOT included in this JSON backup - back up the '
            '"media/" directory separately (e.g. copy it or add it to your regular file backups).'
        )
