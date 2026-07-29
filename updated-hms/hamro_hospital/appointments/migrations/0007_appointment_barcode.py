from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0006_appointment_age_alter_appointment_date_of_birth'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='appointments/barcodes/'),
        ),
    ]
