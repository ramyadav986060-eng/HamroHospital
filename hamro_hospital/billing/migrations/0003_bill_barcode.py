from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_alter_bill_payment_method_discountrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='billing/barcodes/'),
        ),
    ]
