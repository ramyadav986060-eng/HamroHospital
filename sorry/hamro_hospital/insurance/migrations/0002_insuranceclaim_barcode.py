from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insurance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='insuranceclaim',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='insurance/barcodes/'),
        ),
    ]
