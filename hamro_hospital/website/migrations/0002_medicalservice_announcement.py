import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('departments', '0002_departmentunit'),
        ('website', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=170, unique=True)),
                ('description', models.TextField()),
                ('icon_class', models.CharField(blank=True, help_text="Bootstrap Icons class, e.g. 'bi bi-heart-pulse'", max_length=60)),
                ('is_active', models.BooleanField(default=True)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='medical_services', to='departments.department',
                    help_text='Optional — links this service to a department so doctors/schedule can be shown.',
                )),
            ],
            options={
                'db_table': 'website_medical_service',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.CharField(max_length=300)),
                ('category', models.CharField(choices=[
                    ('appointment', 'Online Appointment Available'),
                    ('payment', 'eSewa Payment Available'),
                    ('notice', 'Hospital Notice'),
                    ('holiday', 'Holiday Notice'),
                    ('service', 'New Service'),
                ], default='notice', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('publish_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Leave blank to show indefinitely.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'website_announcement',
                'ordering': ['-publish_at'],
            },
        ),
    ]
