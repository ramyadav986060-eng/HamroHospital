from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('appointments', '0007_appointment_barcode')]
    operations = [
        migrations.AddField('appointment', 'is_extension_service', models.BooleanField(default=False)),
    ]
