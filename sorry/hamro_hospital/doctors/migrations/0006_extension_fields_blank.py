from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('doctors', '0005_extension_service_fields')]
    operations = [
        migrations.AlterField('doctor', 'extension_new_fee', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10)),
        migrations.AlterField('doctor', 'extension_old_fee', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10)),
        migrations.AlterField('doctor', 'extension_morning_quota', models.PositiveIntegerField(blank=True, default=0)),
        migrations.AlterField('doctor', 'extension_afternoon_quota', models.PositiveIntegerField(blank=True, default=0)),
    ]
