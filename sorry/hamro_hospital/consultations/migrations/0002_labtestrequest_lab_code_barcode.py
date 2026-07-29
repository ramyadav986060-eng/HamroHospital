from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consultations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='labtestrequest',
            name='lab_code',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=30, unique=True, null=True),
        ),
        migrations.AddField(
            model_name='labtestrequest',
            name='barcode',
            field=models.ImageField(blank=True, null=True, upload_to='laboratory/barcodes/'),
        ),
    ]
