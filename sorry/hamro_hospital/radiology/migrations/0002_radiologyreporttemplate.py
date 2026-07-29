# Generated manually for radiology report templates

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('radiology', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='RadiologyReportTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('service_type', models.CharField(choices=[('xray', 'X-Ray'), ('ct', 'CT Scan'), ('mri', 'MRI'), ('ecg', 'ECG'), ('echo', 'Echo'), ('ultrasound', 'Ultrasound'), ('custom', 'Other / Custom')], default='xray', max_length=20)),
                ('findings_template', models.TextField(blank=True)),
                ('impression_template', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'db_table': 'radiology_report_template', 'ordering': ['name']},
        ),
    ]
