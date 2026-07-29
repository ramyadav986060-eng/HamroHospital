import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from website.models import HomeNotification

if not HomeNotification.objects.exists():
    HomeNotification.objects.create(message="हाम्रो अस्पतालमा तपाईंलाई हार्दिक स्वागत छ।")
