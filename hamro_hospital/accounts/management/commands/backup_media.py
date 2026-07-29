import os
import zipfile
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates a timestamped ZIP backup of MEDIA_ROOT under BASE_DIR/backups/.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default=None, help='Directory to write backup into (default: BASE_DIR/backups)')

    def handle(self, *args, **options):
        output_dir = options['output_dir'] or os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_dir, f'hamro_media_backup_{timestamp}.zip')
        media_root = str(settings.MEDIA_ROOT)
        with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.isdir(media_root):
                for root, _dirs, files in os.walk(media_root):
                    for name in files:
                        full = os.path.join(root, name)
                        arc = os.path.join('media', os.path.relpath(full, media_root))
                        zf.write(full, arc)
            else:
                zf.writestr('media/README.txt', 'MEDIA_ROOT did not exist when this backup was created.\n')
        self.stdout.write(self.style.SUCCESS(f'Media backup written to {filename}'))
