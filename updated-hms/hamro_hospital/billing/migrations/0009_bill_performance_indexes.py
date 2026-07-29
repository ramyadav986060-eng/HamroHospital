from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('billing', '0008_expand_bill_statuses')]
    operations = [
        migrations.AddIndex(model_name='bill', index=models.Index(fields=['status', 'created_at'], name='billing_bil_status_8a5532_idx')),
        migrations.AddIndex(model_name='bill', index=models.Index(fields=['payment_method', 'created_at'], name='billing_bil_payment_0fe2d4_idx')),
        migrations.AddIndex(model_name='bill', index=models.Index(fields=['bill_type', 'created_at'], name='billing_bil_bill_ty_9a1911_idx')),
    ]
