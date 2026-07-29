# Generated manually for central HIS workflow engine

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('patients', '0006_patient_barcode'),
        ('departments', '0002_departmentunit'),
        ('billing', '0007_bill_pending_status'),
        ('referrals', '0003_referral_billing_fields'),
    ]
    operations = [
        migrations.CreateModel(
            name='ServiceOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_role', models.CharField(blank=True, max_length=30)),
                ('destination_role', models.CharField(blank=True, max_length=30)),
                ('service_type', models.CharField(choices=[('opd', 'OPD'), ('laboratory', 'Laboratory'), ('radiology', 'Radiology'), ('pharmacy', 'Pharmacy'), ('admission', 'Admission'), ('nursing', 'Nursing'), ('operation_theatre', 'Operation Theatre'), ('blood_bank', 'Blood Bank'), ('insurance', 'Insurance'), ('other', 'Other')], default='other', max_length=30)),
                ('service_name', models.CharField(max_length=200)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('requested', 'Requested'), ('accepted', 'Accepted'), ('pending_payment', 'Pending Payment'), ('paid', 'Paid'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('rejected', 'Rejected')], default='requested', max_length=20)),
                ('payment_status', models.CharField(choices=[('not_required', 'No Payment Required'), ('pending', 'Payment Pending'), ('paid', 'Payment Paid'), ('insurance_pending', 'Insurance Pending'), ('insurance_approved', 'Insurance Approved')], default='pending', max_length=25)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('bill', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_orders', to='billing.bill')),
                ('destination_department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_orders', to='departments.department')),
                ('ordered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_orders_created', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_orders', to='patients.patient')),
                ('referral', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='service_orders', to='referrals.referral')),
            ],
            options={'db_table': 'workflow_service_order', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PaymentEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(max_length=30)),
                ('transaction_reference', models.CharField(blank=True, max_length=120)),
                ('gateway_response', models.TextField(blank=True)),
                ('remarks', models.TextField(blank=True)),
                ('paid_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_events', to='billing.bill')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_events_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'workflow_payment_event', 'ordering': ['-paid_at']},
        ),
        migrations.CreateModel(
            name='PatientTimeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('registration', 'Registration'), ('visit', 'OPD Visit'), ('consultation', 'Consultation'), ('referral', 'Referral'), ('order', 'Service Order'), ('bill', 'Bill'), ('payment', 'Payment'), ('lab', 'Laboratory'), ('radiology', 'Radiology'), ('pharmacy', 'Pharmacy'), ('admission', 'Admission'), ('discharge', 'Discharge'), ('document', 'Document'), ('blood_bank', 'Blood Bank'), ('other', 'Other')], default='other', max_length=30)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('source_app', models.CharField(blank=True, max_length=60)),
                ('source_model', models.CharField(blank=True, max_length=60)),
                ('source_object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('related_url', models.CharField(blank=True, max_length=255)),
                ('event_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='timeline_events', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_events', to='patients.patient')),
            ],
            options={'db_table': 'workflow_patient_timeline', 'ordering': ['-event_at']},
        ),
        migrations.AddIndex(model_name='serviceorder', index=models.Index(fields=['patient', 'created_at'], name='workflow_se_patient_ba05ed_idx')),
        migrations.AddIndex(model_name='serviceorder', index=models.Index(fields=['service_type', 'status'], name='workflow_se_service_b0d6a2_idx')),
        migrations.AddIndex(model_name='serviceorder', index=models.Index(fields=['payment_status'], name='workflow_se_payment_00d2e6_idx')),
        migrations.AddIndex(model_name='serviceorder', index=models.Index(fields=['bill'], name='workflow_se_bill_id_8c1f88_idx')),
        migrations.AddIndex(model_name='serviceorder', index=models.Index(fields=['referral'], name='workflow_se_referral_3e6d78_idx')),
        migrations.AddIndex(model_name='paymentevent', index=models.Index(fields=['bill', 'paid_at'], name='workflow_pa_bill_id_984ef1_idx')),
        migrations.AddIndex(model_name='paymentevent', index=models.Index(fields=['payment_method'], name='workflow_pa_payment_963d9c_idx')),
        migrations.AddIndex(model_name='patienttimeline', index=models.Index(fields=['patient', '-event_at'], name='workflow_pa_patient_8b5481_idx')),
        migrations.AddIndex(model_name='patienttimeline', index=models.Index(fields=['event_type'], name='workflow_pa_event_t_7b54ca_idx')),
        migrations.AddIndex(model_name='patienttimeline', index=models.Index(fields=['source_app', 'source_model', 'source_object_id'], name='workflow_pa_source__729768_idx')),
    ]
