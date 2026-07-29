from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User, StaffAttendance, StaffSalaryProfile, StaffSalaryPayment, StaffLeaveRequest


class StaffIdentityAttendancePayrollTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin_test', password='password')
        self.finance = User.objects.create_user(username='finance_test', password='password', role=Role.ACCOUNTS_DEPT)
        self.staff = User.objects.create_user(username='staff_test', password='password', role=Role.HOSPITAL_STAFF, first_name='Staff')

    def test_staff_can_login_with_staff_id_and_view_own_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {'username': self.staff.staff_id, 'password': 'password'}, follow=True)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(self.client.get(reverse('accounts:staff_profile')).status_code, 200)

    def test_staff_cannot_open_manual_attendance_correction(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('accounts:staff_attendance_punch'))
        self.assertEqual(response.status_code, 302)

    def test_salary_uses_biometric_attendance_and_is_finance_only(self):
        now = timezone.now()
        StaffAttendance.objects.create(
            staff=self.staff,
            date=now.date(),
            check_in=now.replace(hour=8, minute=0),
            check_out=now.replace(hour=17, minute=0),
            source='fingerprint',
        )
        StaffSalaryProfile.objects.create(staff=self.staff, per_day_salary=Decimal('1000.00'))
        self.client.force_login(self.finance)
        response = self.client.post(reverse('accounts:staff_salary_generate'), {'year': now.year, 'month': now.month})
        self.assertEqual(response.status_code, 302)
        payment = StaffSalaryPayment.objects.get(staff=self.staff, year=now.year, month=now.month)
        self.assertEqual(payment.present_days, 1)
        self.assertEqual(payment.net_amount, Decimal('1000.00'))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('accounts:staff_salary_payments')).status_code, 302)

    def test_approved_leave_blocks_biometric_attendance(self):
        leave = StaffLeaveRequest.objects.create(
            staff=self.staff, leave_type='Paid Leave', start_date=timezone.localdate(),
            end_date=timezone.localdate(), reason='Approved leave test', status=StaffLeaveRequest.Status.APPROVED,
        )
        StaffAttendance.objects.update_or_create(
            staff=self.staff, date=timezone.localdate(),
            defaults={'status': StaffAttendance.Status.LEAVE, 'remarks': 'Approved leave'},
        )
        response = self.client.get(reverse('accounts:staff_attendance_device_punch'), {'staff_id': self.staff.staff_id, 'direction': 'in'})
        self.assertEqual(response.status_code, 409)
        self.assertIn('Attendance not permitted', response.json()['error'])
