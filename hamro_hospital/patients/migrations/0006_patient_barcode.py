# Generated manually to mirror 0005_visit_barcode.py for the new Patient.barcode field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_visit_barcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='patients/barcodes/'),
        ),
    ]
