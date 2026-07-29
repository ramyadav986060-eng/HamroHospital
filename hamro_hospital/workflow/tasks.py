from celery import shared_task


@shared_task
def daily_workflow_summary_task(date=None):
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    args = []
    if date:
        args = ['--date', date]
    call_command('daily_workflow_summary', *args, stdout=out)
    return out.getvalue()


@shared_task
def send_notification_digest_task():
    """Placeholder for scheduled notification/email/SMS digest.
    Returns count of unread notifications so production can wire email/SMS later.
    """
    from accounts.models import Notification
    return Notification.objects.filter(is_read=False).count()
