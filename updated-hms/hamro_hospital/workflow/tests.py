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

class AdmissionWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admission1', password='pass12345', role=Role.WARD_ADMISSION, is_staff=True)
        province = Province.objects.create(number=4, name='Gandaki')
        district = District.objects.create(province=province, name='Kaski')
        self.patient = Patient.objects.create(first_name='Admit', last_name='Patient', gender='F', date_of_birth='1985-01-01', phone_number='9800000002', district=district)
        self.department = Department.objects.create(name='Medicine', slug='medicine-test', description='Medicine', consultation_fee=0)
        from admissions.models import Ward, Bed, Admission
        self.Ward, self.Bed, self.Admission = Ward, Bed, Admission
        self.ward1 = Ward.objects.create(name='General A', ward_type='general', daily_rate=100)
        self.ward2 = Ward.objects.create(name='ICU A', ward_type='icu', daily_rate=5000)
        self.bed1 = Bed.objects.create(ward=self.ward1, bed_number='1', is_occupied=True)
        self.bed2 = Bed.objects.create(ward=self.ward2, bed_number='2', is_occupied=False)
        self.admission = Admission.objects.create(patient=self.patient, department=self.department, ward=self.ward1, bed=self.bed1, reason_for_admission='Observation', created_by=self.user)

    def test_deposit_and_bed_transfer(self):
        from admissions.models import AdmissionDeposit, BedTransfer
        deposit = AdmissionDeposit.objects.create(admission=self.admission, amount=1000, received_by=self.user)
        self.assertEqual(deposit.amount, 1000)
        transfer = BedTransfer.objects.create(admission=self.admission, to_ward=self.ward2, to_bed=self.bed2, transferred_by=self.user)
        self.bed1.refresh_from_db(); self.bed2.refresh_from_db(); self.admission.refresh_from_db()
        self.assertFalse(self.bed1.is_occupied)
        self.assertTrue(self.bed2.is_occupied)
        self.assertEqual(self.admission.ward_id, self.ward2.id)

    def test_discharge_checklist_completion(self):
        from admissions.models import DischargeChecklist
        checklist = DischargeChecklist.objects.create(
            admission=self.admission, all_bills_paid=True, lab_reports_complete=True,
            radiology_reports_complete=True, medicine_charges_complete=True,
            discharge_summary_prepared=True, nursing_clearance=True,
            insurance_clearance=True, bed_release_ready=True,
        )
        self.assertTrue(checklist.is_complete)

class SafetyAndInventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='staff1', password='pass12345', role=Role.CASH_COUNTER, is_staff=True)
        province = Province.objects.create(number=5, name='Lumbini')
        district = District.objects.create(province=province, name='Rupandehi')
        self.patient = Patient.objects.create(first_name='Safe', last_name='Patient', gender='M', date_of_birth='1990-01-01', phone_number='9800000003', district=district, blood_group='A+')

    def test_blood_compatibility(self):
        from blood_bank.models import is_compatible_blood
        self.assertTrue(is_compatible_blood('O-', 'A+'))
        self.assertFalse(is_compatible_blood('B+', 'A+'))

    def test_pharmacy_batch_and_ledger_models(self):
        from pharmacy.models import Medicine, Supplier, MedicineBatch, StockLedger
        med = Medicine.objects.create(medicine_code='M001', name='Paracetamol', category='Tablet', selling_price=10, current_stock=100, minimum_stock=5)
        supplier = Supplier.objects.create(name='Demo Supplier')
        batch = MedicineBatch.objects.create(medicine=med, supplier=supplier, batch_number='B001', quantity_received=50, quantity_available=50, mrp=10)
        StockLedger.objects.create(medicine=med, batch=batch, movement_type=StockLedger.MovementType.PURCHASE, quantity_change=50, balance_after=100, created_by=self.user)
        self.assertEqual(med.batches.count(), 1)
        self.assertEqual(med.stock_ledger.count(), 1)
