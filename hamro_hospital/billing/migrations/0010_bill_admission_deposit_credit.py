from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('billing', '0009_bill_performance_indexes')]
    operations = [
        migrations.AddField(
            model_name='bill',
            name='admission_deposit_credit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
