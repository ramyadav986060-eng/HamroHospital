from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_staff_management'),
    ]
    operations = [
        migrations.AddField(
            model_name='hospitalsetting',
            name='required_daily_working_hours',
            field=models.DecimalField(decimal_places=2, default=9, max_digits=4),
        ),
        migrations.AddField(
            model_name='hospitalsetting',
            name='default_weekend_days',
            field=models.CharField(default='sat', help_text='Comma-separated weekday codes for default holidays, e.g. sat or fri,sat', max_length=30),
        ),
        migrations.CreateModel(
            name='StaffSalaryProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bank_name', models.CharField(blank=True, max_length=150)),
                ('bank_account_name', models.CharField(blank=True, max_length=150)),
                ('bank_account_number', models.CharField(blank=True, max_length=80)),
                ('pan_number', models.CharField(blank=True, max_length=80)),
                ('base_monthly_salary', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('per_day_salary', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('bonus_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('overtime_rate_per_hour', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('staff', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='salary_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'accounts_staff_salary_profile'},
        ),
        migrations.CreateModel(
            name='StaffSalaryPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveIntegerField()),
                ('month', models.PositiveIntegerField()),
                ('working_days', models.PositiveIntegerField(default=0)),
                ('present_days', models.PositiveIntegerField(default=0)),
                ('leave_days', models.PositiveIntegerField(default=0)),
                ('absent_days', models.PositiveIntegerField(default=0)),
                ('base_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('bonus_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('overtime_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('deductions', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('net_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('approved', 'Approved'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], default='draft', max_length=15)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('prepared_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='salary_payments_prepared', to=settings.AUTH_USER_MODEL)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salary_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'accounts_staff_salary_payment', 'ordering': ['-year', '-month', 'staff__first_name'], 'unique_together': {('staff', 'year', 'month')}},
        ),
        migrations.AddIndex(model_name='staffsalarypayment', index=models.Index(fields=['year', 'month', 'status'], name='accounts_st_year_8809c7_idx')),
        migrations.AddIndex(model_name='staffsalarypayment', index=models.Index(fields=['staff', 'year', 'month'], name='accounts_st_staff_i_72e193_idx')),
    ]
