# Generated manually for staff profile, barcode, attendance and leave management

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('departments', '0002_departmentunit'),
        ('accounts', '0006_notification_related_url'),
    ]
    operations = [
        migrations.AddField(
            model_name='user',
            name='staff_id',
            field=models.CharField(blank=True, db_index=True, max_length=30, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='staff_barcode',
            field=models.ImageField(blank=True, null=True, upload_to='staff/barcodes/'),
        ),
        migrations.AddField(
            model_name='user',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff_users', to='departments.department'),
        ),
        migrations.AddField(
            model_name='user',
            name='designation',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='user',
            name='is_department_head',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='hospitalsetting',
            name='staff_discount_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='hospitalsetting',
            name='staff_discount_percent',
            field=models.DecimalField(decimal_places=2, default=90, max_digits=5),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('super_admin', 'Super Admin'), ('registration_counter', 'Registration Counter'), ('cash_counter', 'Cash Counter'), ('doctor', 'Doctor'), ('pharmacy', 'Pharmacy'), ('laboratory', 'Laboratory'), ('radiology', 'Radiology Counter'), ('insurance', 'Insurance Counter'), ('ward_admission', 'Ward / Admission'), ('nursing', 'Nursing'), ('operation_theatre', 'Operation Theatre'), ('blood_bank', 'Blood Bank'), ('accounts_dept', 'Finance'), ('medical_records', 'Medical Records'), ('department_head', 'Department Head / Sub-Admin')], default='registration_counter', help_text='Primary role used to route the dashboard and gate permissions.', max_length=30),
        ),
        migrations.CreateModel(
            name='StaffAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('check_in', models.DateTimeField(blank=True, null=True)),
                ('check_out', models.DateTimeField(blank=True, null=True)),
                ('total_working_hours', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('status', models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'Approved Leave'), ('holiday', 'Holiday / Weekend'), ('partial', 'Partial')], default='absent', max_length=15)),
                ('source', models.CharField(blank=True, default='manual', help_text='manual, fingerprint, import, etc.', max_length=50)),
                ('device_log_id', models.CharField(blank=True, max_length=100)),
                ('remarks', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'accounts_staff_attendance', 'ordering': ['-date', 'staff__first_name'], 'unique_together': {('staff', 'date')}},
        ),
        migrations.CreateModel(
            name='StaffLeaveRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leave_type', models.CharField(default='General Leave', max_length=50)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=15)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='leave_requests_reviewed', to=settings.AUTH_USER_MODEL)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'accounts_staff_leave_request', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='staffattendance', index=models.Index(fields=['staff', 'date'], name='accounts_st_staff__c3a295_idx')),
        migrations.AddIndex(model_name='staffattendance', index=models.Index(fields=['date', 'status'], name='accounts_st_date_ae15ab_idx')),
        migrations.AddIndex(model_name='staffleaverequest', index=models.Index(fields=['staff', 'status'], name='accounts_st_staff__9d4087_idx')),
        migrations.AddIndex(model_name='staffleaverequest', index=models.Index(fields=['start_date', 'end_date'], name='accounts_st_start_d_ddfbf8_idx')),
    ]
