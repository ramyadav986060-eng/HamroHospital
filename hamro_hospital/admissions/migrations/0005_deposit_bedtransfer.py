# Generated manually for admission deposits and bed transfers

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('admissions', '0004_discharge_checklist'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AdmissionDeposit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deposit_type', models.CharField(choices=[('deposit', 'Deposit'), ('used', 'Used Against Bill'), ('refund', 'Refund')], default='deposit', max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(default='cash', max_length=30)),
                ('receipt_number', models.CharField(blank=True, max_length=50)),
                ('remarks', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deposits', to='admissions.admission')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admission_deposits_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admissions_deposit', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='BedTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('transferred_at', models.DateTimeField(auto_now_add=True)),
                ('admission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bed_transfers', to='admissions.admission')),
                ('from_bed', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfers_from', to='admissions.bed')),
                ('from_ward', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfers_from', to='admissions.ward')),
                ('to_bed', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transfers_to', to='admissions.bed')),
                ('to_ward', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transfers_to', to='admissions.ward')),
                ('transferred_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bed_transfers_done', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admissions_bed_transfer', 'ordering': ['-transferred_at']},
        ),
    ]
