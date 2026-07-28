from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Validate production-critical HIS settings such as Redis, Celery and eSewa.'

    def handle(self, *args, **options):
        warnings = []
        errors = []

        if settings.DEBUG:
            warnings.append('DJANGO_DEBUG=True. Set DJANGO_DEBUG=False for production.')
        if not getattr(settings, 'REDIS_URL', ''):
            warnings.append('REDIS_URL is not configured. WebSockets/Celery will use local development fallback only.')
        if not getattr(settings, 'CELERY_BROKER_URL', ''):
            warnings.append('CELERY_BROKER_URL is not configured.')
        if not getattr(settings, 'CELERY_RESULT_BACKEND', ''):
            warnings.append('CELERY_RESULT_BACKEND is not configured.')
        if not getattr(settings, 'ESEWA_MERCHANT_CODE', ''):
            errors.append('ESEWA_MERCHANT_CODE is missing.')
        if not getattr(settings, 'ESEWA_SECRET_KEY', ''):
            errors.append('ESEWA_SECRET_KEY is missing.')
        if not settings.ESEWA_SANDBOX and settings.ESEWA_MERCHANT_CODE == 'EPAYTEST':
            errors.append('Live eSewa cannot use EPAYTEST merchant code.')

        for msg in warnings:
            self.stdout.write(self.style.WARNING('WARNING: ' + msg))
        for msg in errors:
            self.stdout.write(self.style.ERROR('ERROR: ' + msg))

        if errors:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS('Production configuration check completed.'))
