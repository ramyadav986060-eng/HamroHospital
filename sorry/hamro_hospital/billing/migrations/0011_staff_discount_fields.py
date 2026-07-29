from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0010_bill_admission_deposit_credit'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='bill',
            name='staff_beneficiary',
            field=models.ForeignKey(blank=True, help_text='Staff member receiving staff benefit discount, if applicable.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff_discount_bills', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='bill',
            name='staff_discount_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='bill',
            name='staff_discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
