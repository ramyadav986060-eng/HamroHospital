import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0002_departmentunit'),
        ('doctors', '0002_doctor_quota_leave'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='short_introduction',
            field=models.CharField(
                blank=True, max_length=300,
                help_text='One or two lines shown on the public doctor profile (kept short by design).',
            ),
        ),
        migrations.AddField(
            model_name='doctor',
            name='contact_number',
            field=models.CharField(blank=True, help_text='Optional — shown on public profile if set.', max_length=20),
        ),
        migrations.AddField(
            model_name='doctor',
            name='unit',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='doctors', to='departments.departmentunit',
                help_text='Optional sub-unit within the department (e.g. Unit 1).',
            ),
        ),
        migrations.CreateModel(
            name='DoctorSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.CharField(choices=[('sun', 'Sunday'), ('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'), ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday')], max_length=3)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('room_or_unit_note', models.CharField(blank=True, help_text='e.g. "OPD Room 12"', max_length=100)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='doctors.doctor')),
            ],
            options={
                'db_table': 'doctors_doctorschedule',
                'ordering': ['doctor', 'weekday'],
                'unique_together': {('doctor', 'weekday')},
            },
        ),
    ]
