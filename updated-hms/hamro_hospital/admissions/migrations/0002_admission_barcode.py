from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='admission',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='admissions/barcodes/'),
        ),
    ]
