from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone

from workflow.models import ServiceOrder, PaymentEvent


class Command(BaseCommand):
    help = 'Print a daily workflow/payment summary. Intended for cron/Celery scheduling.'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='Date in YYYY-MM-DD format. Defaults to today.')

    def handle(self, *args, **options):
        import datetime
        day = timezone.now().date()
        if options.get('date'):
            day = datetime.date.fromisoformat(options['date'])
        orders = ServiceOrder.objects.filter(created_at__date=day)
        payments = PaymentEvent.objects.filter(paid_at__date=day)
        self.stdout.write(self.style.SUCCESS(f'Workflow summary for {day}'))
        self.stdout.write(f'Orders created: {orders.count()}')
        for row in orders.values('service_type').annotate(count=Count('id')).order_by('service_type'):
            self.stdout.write(f"  {row['service_type']}: {row['count']}")
        self.stdout.write(f"Payments: {payments.count()} | Total: NPR {payments.aggregate(t=Sum('amount'))['t'] or 0}")
