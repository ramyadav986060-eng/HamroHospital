import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('doctors', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoctorLeave',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('reason', models.CharField(blank=True, help_text='e.g. Leave, Holiday, Off Duty, Conference', max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leaves', to='doctors.doctor')),
            ],
            options={
                'db_table': 'doctors_doctorleave',
                'ordering': ['-date'],
                'unique_together': {('doctor', 'date')},
            },
        ),
        migrations.CreateModel(
            name='DoctorWeeklyQuota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.CharField(choices=[('sun', 'Sunday'), ('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'), ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday')], max_length=3)),
                ('quota', models.PositiveIntegerField(default=0)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_quotas', to='doctors.doctor')),
            ],
            options={
                'db_table': 'doctors_doctorweeklyquota',
                'ordering': ['doctor', 'weekday'],
                'unique_together': {('doctor', 'weekday')},
            },
        ),
        migrations.CreateModel(
            name='DoctorQuotaOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('quota', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quota_overrides', to='doctors.doctor')),
            ],
            options={
                'db_table': 'doctors_doctorquotaoverride',
                'ordering': ['-date'],
                'unique_together': {('doctor', 'date')},
            },
        ),
    ]
