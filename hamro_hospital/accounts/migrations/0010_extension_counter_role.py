from django.db import migrations, models


ROLE_CHOICES = [
    ('super_admin', 'Super Admin'),
    ('registration_counter', 'Registration Counter'),
    ('extension_counter', 'EHS Counter'),
    ('cash_counter', 'Cash Counter'),
    ('doctor', 'Doctor'),
    ('pharmacy', 'Pharmacy'),
    ('laboratory', 'Laboratory'),
    ('radiology', 'Radiology Counter'),
    ('insurance', 'Insurance Counter'),
    ('ward_admission', 'Ward / Admission'),
    ('nursing', 'Nursing'),
    ('operation_theatre', 'Operation Theatre'),
    ('blood_bank', 'Blood Bank'),
    ('accounts_dept', 'Finance'),
    ('medical_records', 'Medical Records'),
    ('department_head', 'Department Head / Sub-Admin'),
]


class Migration(migrations.Migration):
    dependencies = [('accounts', '0009_leave_policy_limits')]
    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=ROLE_CHOICES, default='registration_counter', help_text='Primary role used to route the dashboard and gate permissions.', max_length=30),
        ),
        migrations.AlterField(
            model_name='notification',
            name='role',
            field=models.CharField(blank=True, choices=ROLE_CHOICES, help_text='Target role (e.g. all Laboratory staff).', max_length=30, null=True),
        ),
    ]
