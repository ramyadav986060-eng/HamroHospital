import os
import zipfile
from datetime import datetime
from io import StringIO

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates one timestamped ZIP containing database JSON and media files under BASE_DIR/backups/.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default=None, help='Directory to write backup into (default: BASE_DIR/backups)')

    def handle(self, *args, **options):
        output_dir = options['output_dir'] or os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'hamro_full_backup_{timestamp}.zip')
        dump = StringIO()
        management.call_command(
            'dumpdata',
            exclude=['contenttypes', 'auth.permission', 'sessions.session', 'admin.logentry'],
            indent=2,
            stdout=dump,
        )
        media_root = str(settings.MEDIA_ROOT)
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('database.json', dump.getvalue())
            zf.writestr('RESTORE_INSTRUCTIONS.txt', 'Restore database: python manage.py restore_data database.json --yes\nRestore media: extract media/ into MEDIA_ROOT after verifying backup integrity.\n')
            if os.path.isdir(media_root):
                for root, _dirs, files in os.walk(media_root):
                    for name in files:
                        full = os.path.join(root, name)
                        arc = os.path.join('media', os.path.relpath(full, media_root))
                        zf.write(full, arc)
        self.stdout.write(self.style.SUCCESS(f'Full backup written to {filename}'))
