# Generated manually for pending department bill workflow

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0006_bill_blood_bank_type'),
    ]
    operations = [
        migrations.AlterField(
            model_name='bill',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('refunded', 'Refunded')], default='paid', max_length=10),
        ),
    ]
