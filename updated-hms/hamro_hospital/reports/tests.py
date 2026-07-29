from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User


class OfficialReportAccessAndExportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin_report_test', password='password')
        self.finance = User.objects.create_user(username='finance_report_test', password='password', role=Role.ACCOUNTS_DEPT)
        self.department_head = User.objects.create_user(username='dept_head_report_test', password='password', role=Role.DEPARTMENT_HEAD)

    def test_super_admin_can_export_core_reports_pdf_and_excel(self):
        self.client.force_login(self.admin)
        report_names = [
            'reports:revenue_dashboard',
            'reports:finance_report',
            'reports:staff_attendance_report',
            'reports:payroll_report',
            'reports:admission_report',
            'reports:laboratory_report',
            'reports:radiology_report',
            'reports:pharmacy_report',
            'reports:insurance_report',
            'reports:department_revenue_report',
        ]
        for name in report_names:
            url = reverse(name)
            pdf_response = self.client.get(url, {'date_filter': 'today', 'export': 'pdf'})
            self.assertEqual(pdf_response.status_code, 200, name)
            self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
            excel_response = self.client.get(url, {'date_filter': 'today', 'export': 'excel'})
            self.assertEqual(excel_response.status_code, 200, name)
            self.assertIn('spreadsheetml.sheet', excel_response['Content-Type'])

    def test_finance_can_access_financial_staff_and_payroll_reports(self):
        self.client.force_login(self.finance)
        for name in ['reports:finance_report', 'reports:staff_attendance_report', 'reports:staff_leave_report', 'reports:payroll_report']:
            response = self.client.get(reverse(name), {'date_filter': 'today'})
            self.assertEqual(response.status_code, 200, name)

    def test_department_head_is_scoped_away_from_confidential_finance_reports(self):
        self.client.force_login(self.department_head)
        self.assertEqual(self.client.get(reverse('reports:department_report')).status_code, 200)
        self.assertEqual(self.client.get(reverse('reports:doctor_report')).status_code, 200)
        self.assertEqual(self.client.get(reverse('reports:registration_report')).status_code, 200)
        confidential = [
            'reports:finance_report',
            'reports:payroll_report',
            'reports:staff_attendance_report',
            'reports:department_revenue_report',
        ]
        for name in confidential:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
