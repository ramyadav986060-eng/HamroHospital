"""Celery application for background HIS jobs.

Run worker in production with:
    celery -A config worker -l info
Run beat/scheduler if needed with:
    celery -A config beat -l info
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('hamro_hospital')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
