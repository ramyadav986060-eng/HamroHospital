from django.test import TestCase
from django.urls import reverse

from accounts.models import User, Role
from departments.models import Department
from patients.models import Patient, Province, District
from referrals.models import Referral
from workflow.models import ServiceOrder, PaymentEvent, PatientTimeline
from workflow.utils import create_orders_for_referral, record_payment_event
from billing.models import Bill, PaymentMethod


class WorkflowEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='doctor1', password='pass12345', role=Role.DOCTOR, is_staff=True)
        province = Province.objects.create(number=3, name='Bagmati')
        district = District.objects.create(province=province, name='Kathmandu')
        self.patient = Patient.objects.create(first_name='Test', last_name='Patient', gender='M', date_of_birth='1990-01-01', phone_number='9800000001', district=district)
        self.department = Department.objects.create(name='Laboratory', slug='laboratory', description='Lab', consultation_fee=0)

    def test_referral_creates_service_order(self):
        referral = Referral.objects.create(patient=self.patient, referral_type=Referral.ReferralType.LABORATORY, to_department=self.department, reason='CBC', requested_items='CBC', created_by=self.user)
        orders = create_orders_for_referral(referral, actor=self.user)
        self.assertEqual(len(orders), 1)
        self.assertEqual(ServiceOrder.objects.filter(referral=referral).count(), 1)
        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event_type=PatientTimeline.EventType.REFERRAL).exists())

    def test_payment_event_marks_orders_paid(self):
        referral = Referral.objects.create(patient=self.patient, referral_type=Referral.ReferralType.LABORATORY, to_department=self.department, reason='CBC', requested_items='CBC', created_by=self.user)
        order = create_orders_for_referral(referral, actor=self.user)[0]
        bill = Bill.objects.create(patient=self.patient, cashier=self.user, payment_method=PaymentMethod.CASH, status=Bill.Status.PENDING)
        order.bill = bill
        order.save(update_fields=['bill'])
        bill.status = Bill.Status.PAID
        bill.save(update_fields=['status'])
        record_payment_event(bill, amount=100, method=PaymentMethod.CASH, received_by=self.user)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, ServiceOrder.PaymentStatus.PAID)
        self.assertTrue(PaymentEvent.objects.filter(bill=bill).exists())
