# Generated manually for professional laboratory panels/parameters

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('laboratory', '0001_initial'),
        ('consultations', '0008_verification_fields'),
    ]
    operations = [
        migrations.CreateModel(
            name='LabPanel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'db_table': 'laboratory_panel', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='LabParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('unit', models.CharField(blank=True, max_length=50)),
                ('normal_range', models.CharField(blank=True, max_length=150)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='laboratory.labpanel')),
            ],
            options={'db_table': 'laboratory_parameter', 'ordering': ['panel', 'display_order', 'name'], 'unique_together': {('panel', 'name')}},
        ),
        migrations.CreateModel(
            name='LabResultValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100)),
                ('flag', models.CharField(blank=True, help_text='e.g. High, Low, Critical', max_length=20)),
                ('remarks', models.CharField(blank=True, max_length=255)),
                ('lab_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameter_values', to='consultations.labtestrequest')),
                ('parameter', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='result_values', to='laboratory.labparameter')),
            ],
            options={'db_table': 'laboratory_result_value', 'ordering': ['parameter__display_order', 'parameter__name'], 'unique_together': {('lab_request', 'parameter')}},
        ),
    ]
