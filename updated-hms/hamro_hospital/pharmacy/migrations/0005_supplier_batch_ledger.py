# Generated manually for professional pharmacy batch and stock ledger

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pharmacy', '0004_expand_payment_methods'),
    ]
    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('contact_person', models.CharField(blank=True, max_length=150)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'db_table': 'pharmacy_supplier', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='MedicineBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(max_length=100)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('purchase_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('mrp', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('quantity_received', models.PositiveIntegerField(default=0)),
                ('quantity_available', models.PositiveIntegerField(default=0)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='pharmacy.medicine')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='medicine_batches', to='pharmacy.supplier')),
            ],
            options={'db_table': 'pharmacy_medicine_batch', 'ordering': ['expiry_date', 'medicine__name'], 'unique_together': {('medicine', 'batch_number')}},
        ),
        migrations.CreateModel(
            name='StockLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('purchase', 'Purchase'), ('sale', 'Sale'), ('adjustment', 'Adjustment'), ('return', 'Return'), ('expired', 'Expired / Write-off')], max_length=20)),
                ('quantity_change', models.IntegerField()),
                ('balance_after', models.IntegerField()),
                ('reference', models.CharField(blank=True, max_length=120)),
                ('remarks', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_entries', to='pharmacy.medicinebatch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_ledger_entries', to=settings.AUTH_USER_MODEL)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_ledger', to='pharmacy.medicine')),
            ],
            options={'db_table': 'pharmacy_stock_ledger', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='stockledger', index=models.Index(fields=['medicine', 'created_at'], name='pharmacy_st_medicine_3d979c_idx')),
    ]
