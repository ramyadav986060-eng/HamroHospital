# Generated manually for doctor referral workflow improvements

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0002_departmentunit'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('referrals', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referral',
            name='to_department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals_received', to='departments.department'),
        ),
        migrations.AlterField(
            model_name='referral',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('acknowledged', 'Acknowledged'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='new', max_length=20),
        ),
        migrations.AddField(
            model_name='referral',
            name='referral_type',
            field=models.CharField(choices=[('general', 'General Department'), ('laboratory', 'Laboratory'), ('radiology', 'Radiology'), ('pharmacy', 'Pharmacy'), ('nursing', 'Nursing'), ('admission', 'Admission / Ward'), ('operation_theatre', 'Operation Theatre (OT)'), ('blood_bank', 'Blood Bank')], default='general', max_length=30),
        ),
        migrations.AddField(
            model_name='referral',
            name='diagnosis',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='referral',
            name='clinical_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='referral',
            name='instructions',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='referral',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='referrals/attachments/'),
        ),
        migrations.AddField(
            model_name='referral',
            name='acknowledged_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals_acknowledged', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='referral',
            name='acknowledged_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='referral',
            name='completed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals_completed', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='referral',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
