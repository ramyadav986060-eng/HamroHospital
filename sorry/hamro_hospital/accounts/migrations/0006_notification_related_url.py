# Generated manually for admin/referral notification links

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_auditlog_blood_requested_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='related_url',
            field=models.CharField(blank=True, help_text='Optional URL opened when the notification is clicked.', max_length=255),
        ),
    ]
