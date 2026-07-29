from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_patient_age_at_registration_insurancecategory_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='known_allergies',
            field=models.CharField(blank=True, help_text='e.g. Penicillin, Sulfa drugs, Latex', max_length=255),
        ),
    ]
