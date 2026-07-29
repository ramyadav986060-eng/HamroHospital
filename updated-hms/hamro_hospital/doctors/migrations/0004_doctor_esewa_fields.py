# Generated manually for optional doctor eSewa profile fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('doctors', '0003_doctor_schedule_and_profile_fields'),
    ]
    operations = [
        migrations.AddField(
            model_name='doctor',
            name='esewa_id',
            field=models.CharField(blank=True, help_text='Optional eSewa ID / merchant reference for doctor payments if used.', max_length=100),
        ),
        migrations.AddField(
            model_name='doctor',
            name='esewa_phone',
            field=models.CharField(blank=True, help_text='Optional eSewa phone number.', max_length=20),
        ),
    ]
