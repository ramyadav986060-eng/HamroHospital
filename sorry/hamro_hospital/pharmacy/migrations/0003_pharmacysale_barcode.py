from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0002_alter_pharmacysale_payment_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='pharmacysale',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='pharmacy/barcodes/'),
        ),
    ]
