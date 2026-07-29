from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('patients', '0006_patient_barcode')]
    operations = [
        migrations.AlterField('visit', 'patient_type', models.CharField(choices=[('new', 'New Patient'), ('old', 'Old Patient'), ('extension', 'Extension Service')], max_length=10)),
        migrations.AddField('visit', 'is_extension_service', models.BooleanField(default=False)),
    ]
