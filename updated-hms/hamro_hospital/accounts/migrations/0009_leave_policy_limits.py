from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0008_staff_payroll_settings')]
    operations = [
        migrations.AddField(
            model_name='hospitalsetting',
            name='paid_leave_days_per_month',
            field=models.PositiveIntegerField(default=5, help_text='Standard paid leave days allowed per month before Super Admin override is required.'),
        ),
        migrations.AddField(
            model_name='staffleaverequest',
            name='requires_super_admin_override',
            field=models.BooleanField(default=False),
        ),
    ]
