from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0004_alter_appointment_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='payment_method',
            field=models.CharField(choices=[
                ('cash', 'Cash on Arrival'), ('esewa', 'eSewa'), ('khalti', 'Khalti'),
                ('phonepe', 'PhonePe'), ('mobile_banking', 'Mobile Banking'),
                ('fonepay', 'FonePay'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card Payment'),
            ], default='cash', max_length=15),
        ),
    ]
