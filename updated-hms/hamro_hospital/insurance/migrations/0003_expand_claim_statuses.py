# Generated manually for professional insurance claim lifecycle

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('insurance', '0002_insuranceclaim_barcode')]
    operations = [
        migrations.AlterField(
            model_name='insuranceclaim',
            name='status',
            field=models.CharField(choices=[('created', 'Claim Created'), ('submitted', 'Submitted'), ('under_review', 'Under Review'), ('pending', 'Pending'), ('approved', 'Approved'), ('partially_approved', 'Partially Approved'), ('rejected', 'Rejected'), ('settled', 'Settled')], default='created', max_length=20),
        ),
    ]
