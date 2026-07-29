from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0003_pharmacysale_barcode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pharmacysale',
            name='payment_method',
            field=models.CharField(choices=[
                ('cash', 'Cash'), ('esewa', 'eSewa'), ('khalti', 'Khalti'),
                ('phonepe', 'PhonePe'), ('mobile_banking', 'Mobile Banking'),
                ('fonepay', 'FonePay'), ('bank_transfer', 'Bank Transfer'),
                ('card', 'Card Payment'), ('insurance', 'Insurance'), ('credit', 'Credit'),
            ], max_length=15),
        ),
    ]
