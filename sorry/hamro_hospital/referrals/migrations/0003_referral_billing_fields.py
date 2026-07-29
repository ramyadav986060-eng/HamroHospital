# Generated manually for referral billing workflow

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0007_bill_pending_status'),
        ('referrals', '0002_referral_workflow_fields'),
    ]
    operations = [
        migrations.AddField(
            model_name='referral',
            name='requested_items',
            field=models.TextField(blank=True, help_text='Structured requested services/tests/medicines, one per line.'),
        ),
        migrations.AddField(
            model_name='referral',
            name='related_bill',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to='billing.bill'),
        ),
    ]
