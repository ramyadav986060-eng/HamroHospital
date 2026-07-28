from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operation_theatre', '0002_operationtype_surgery_operation_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='surgery',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='operation_theatre/barcodes/'),
        ),
    ]
