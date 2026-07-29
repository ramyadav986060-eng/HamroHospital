# Generated manually for professional bill lifecycle states

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0007_bill_pending_status'),
    ]
    operations = [
        migrations.AlterField(
            model_name='bill',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending Payment'), ('partial', 'Partially Paid'), ('paid', 'Paid'), ('insurance_pending', 'Insurance Pending'), ('insurance_approved', 'Insurance Approved'), ('refund_requested', 'Refund Requested'), ('refunded', 'Refunded'), ('cancelled', 'Cancelled')], default='paid', max_length=20),
        ),
    ]
