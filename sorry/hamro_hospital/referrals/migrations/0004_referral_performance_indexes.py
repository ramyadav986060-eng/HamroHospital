from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('referrals', '0003_referral_billing_fields')]
    operations = [
        migrations.AddIndex(model_name='referral', index=models.Index(fields=['referral_type', 'status'], name='referrals_r_referral_dbe7fe_idx')),
        migrations.AddIndex(model_name='referral', index=models.Index(fields=['patient', 'created_at'], name='referrals_r_patient__79fc65_idx')),
        migrations.AddIndex(model_name='referral', index=models.Index(fields=['created_by', 'created_at'], name='referrals_r_created_9f76b8_idx')),
    ]
