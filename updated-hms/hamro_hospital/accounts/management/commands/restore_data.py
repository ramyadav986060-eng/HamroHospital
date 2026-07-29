import os

from django.core import management
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Restores the database from a JSON backup created by backup_data. '
        'This loads data into the CURRENT database - run against an empty/migrated '
        'database, or be aware existing rows with matching primary keys will be overwritten.'
    )

    def add_arguments(self, parser):
        parser.add_argument('backup_file', type=str, help='Path to the .json backup file to restore')
        parser.add_argument(
            '--yes', action='store_true',
            help='Skip the confirmation prompt (for scripted/non-interactive restores)',
        )

    def handle(self, *args, **options):
        path = options['backup_file']
        if not os.path.exists(path):
            raise CommandError(f'Backup file not found: {path}')

        if not options['yes']:
            confirm = input(
                f'This will load data from "{path}" into the current database. '
                'Existing rows with matching IDs will be overwritten. Continue? [y/N] '
            )
            if confirm.strip().lower() != 'y':
                self.stdout.write('Restore cancelled.')
                return

        management.call_command('loaddata', path)
        self.stdout.write(self.style.SUCCESS(f'Restore complete from {path}'))
        self.stdout.write(
            'Reminder: uploaded files under MEDIA_ROOT are not part of this restore - '
            'restore the "media/" directory separately if needed.'
        )
