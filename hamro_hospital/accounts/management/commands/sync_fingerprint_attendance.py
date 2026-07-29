import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User, StaffAttendance


class Command(BaseCommand):
    help = 'Import fingerprint attendance CSV: staff_id,timestamp,direction(optional in/out),device_log_id(optional)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file')

    def handle(self, *args, **options):
        path = options['csv_file']
        count = 0
        try:
            fh = open(path, newline='', encoding='utf-8-sig')
        except OSError as exc:
            raise CommandError(str(exc))
        with fh:
            reader = csv.DictReader(fh)
            for row in reader:
                staff_id = (row.get('staff_id') or row.get('staff') or '').strip()
                ts = (row.get('timestamp') or row.get('time') or '').strip()
                direction = (row.get('direction') or '').strip().lower()
                if not staff_id or not ts:
                    continue
                staff = User.objects.filter(staff_id__iexact=staff_id).first()
                if not staff:
                    self.stdout.write(self.style.WARNING(f'Skipped unknown staff: {staff_id}'))
                    continue
                try:
                    dt = datetime.fromisoformat(ts)
                except ValueError:
                    self.stdout.write(self.style.WARNING(f'Skipped invalid timestamp: {ts}'))
                    continue
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                att, _ = StaffAttendance.objects.get_or_create(staff=staff, date=dt.date(), defaults={'source': 'fingerprint'})
                if att.status in [StaffAttendance.Status.LEAVE, StaffAttendance.Status.HOLIDAY]:
                    self.stdout.write(self.style.WARNING(f'Skipped {staff_id} on {dt.date()}: attendance not permitted ({att.get_status_display()}).'))
                    continue
                if direction == 'out':
                    att.check_out = dt
                elif direction == 'in':
                    att.check_in = dt
                else:
                    if not att.check_in or dt < att.check_in:
                        att.check_in = dt
                    if not att.check_out or dt > att.check_out:
                        att.check_out = dt
                att.source = 'fingerprint'
                att.device_log_id = row.get('device_log_id', att.device_log_id)
                att.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Imported {count} fingerprint attendance rows.'))
