from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('doctors', '0004_doctor_esewa_fields')]
    operations = [
        migrations.AddField('doctor', 'is_extension_service', models.BooleanField(default=False, help_text='Available for paid Extension Service consultations outside regular OPD hours.')),
        migrations.AddField('doctor', 'extension_new_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField('doctor', 'extension_old_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField('doctor', 'extension_weekly_off_day', models.CharField(blank=True, choices=[('sun', 'Sunday'), ('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'), ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday')], max_length=3)),
        migrations.AddField('doctor', 'extension_morning_start', models.TimeField(blank=True, null=True)),
        migrations.AddField('doctor', 'extension_morning_end', models.TimeField(blank=True, null=True)),
        migrations.AddField('doctor', 'extension_morning_quota', models.PositiveIntegerField(default=0)),
        migrations.AddField('doctor', 'extension_afternoon_start', models.TimeField(blank=True, null=True)),
        migrations.AddField('doctor', 'extension_afternoon_end', models.TimeField(blank=True, null=True)),
        migrations.AddField('doctor', 'extension_afternoon_quota', models.PositiveIntegerField(default=0)),
    ]
