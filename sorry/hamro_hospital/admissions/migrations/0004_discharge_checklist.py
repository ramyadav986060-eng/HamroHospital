# Generated manually for admission discharge checklist

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0003_ward_daily_rate'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='DischargeChecklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('all_bills_paid', models.BooleanField(default=False)),
                ('lab_reports_complete', models.BooleanField(default=False)),
                ('radiology_reports_complete', models.BooleanField(default=False)),
                ('medicine_charges_complete', models.BooleanField(default=False)),
                ('discharge_summary_prepared', models.BooleanField(default=False)),
                ('nursing_clearance', models.BooleanField(default=False)),
                ('insurance_clearance', models.BooleanField(default=False)),
                ('bed_release_ready', models.BooleanField(default=False)),
                ('remarks', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('admission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='discharge_checklist', to='admissions.admission')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discharge_checklists_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admissions_discharge_checklist'},
        ),
    ]
