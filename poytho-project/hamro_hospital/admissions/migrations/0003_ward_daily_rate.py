# Generated manually for admission billing rates

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0002_admission_barcode'),
    ]
    operations = [
        migrations.AddField(
            model_name='ward',
            name='daily_rate',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Default daily admission charge for this ward/bed type.', max_digits=10),
        ),
    ]
