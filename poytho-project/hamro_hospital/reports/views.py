import datetime
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role, User, StaffAttendance, StaffLeaveRequest, StaffSalaryPayment
from billing.models import Bill, PaymentMethod, BillType
from pharmacy.models import PharmacySale
from patients.models import Visit, Patient
from departments.models import Department
from doctors.models import Doctor
from consultations.models import LabTestRequest, RadiologyRequest, RequestStatus
from reports.excel_utils import export_rows_to_excel, export_rows_to_pdf


FINANCE_ROLES = (Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
REPORT_ROLES = (
    Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD,
    Role.LABORATORY, Role.RADIOLOGY, Role.PHARMACY, Role.WARD_ADMISSION,
    Role.NURSING, Role.OPERATION_THEATRE, Role.BLOOD_BANK, Role.INSURANCE,
)


def _money(value):
    return f'NPR {(value or Decimal("0")):,.2f}'


def _display_user(user):
    return user.get_full_name() or user.username if getattr(user, 'is_authenticated', False) else 'System'


def _date_range_context(filters):
    labels = {
        'today': 'Today', 'yesterday': 'Yesterday', 'last_7': 'Last 7 Days', 'last_30': 'Last 30 Days',
        'week': 'This Week', 'weekly': 'This Week', 'month': 'This Month', 'monthly': 'This Month',
        'year': 'This Year', 'yearly': 'This Year', 'all': 'All Time', 'all_time': 'All Time',
        'custom': f"Custom Date Range ({filters.get('start_date') or '...'} to {filters.get('end_date') or '...'})",
    }
    return labels.get(filters.get('date_filter') or 'today', 'Today')


def _is_finance_user(user):
    return user.is_superuser or user.effective_role in FINANCE_ROLES


def _is_department_head(user):
    return (not user.is_superuser) and user.effective_role == Role.DEPARTMENT_HEAD


def apply_report_filters(qs, request, date_field, search_fields=None):
    """Shared date/search filtering for all official reports."""
    today = timezone.localdate()
    date_filter = request.GET.get('date_filter', 'today')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    q = request.GET.get('q', '').strip()

    if date_filter == 'today':
        qs = qs.filter(**{date_field: today})
    elif date_filter == 'yesterday':
        qs = qs.filter(**{date_field: today - datetime.timedelta(days=1)})
    elif date_filter in ('last_7', '7_days'):
        qs = qs.filter(**{f'{date_field}__gte': today - datetime.timedelta(days=6)})
    elif date_filter in ('last_30', '30_days'):
        qs = qs.filter(**{f'{date_field}__gte': today - datetime.timedelta(days=29)})
    elif date_filter in ('week', 'weekly'):
        qs = qs.filter(**{f'{date_field}__gte': today - datetime.timedelta(days=today.weekday())})
    elif date_filter in ('month', 'monthly'):
        qs = qs.filter(**{f'{date_field}__gte': today.replace(day=1)})
    elif date_filter in ('year', 'yearly'):
        qs = qs.filter(**{f'{date_field}__gte': today.replace(month=1, day=1)})
    elif date_filter == 'custom':
        try:
            if start_date:
                qs = qs.filter(**{f'{date_field}__gte': datetime.date.fromisoformat(start_date)})
            if end_date:
                qs = qs.filter(**{f'{date_field}__lte': datetime.date.fromisoformat(end_date)})
        except ValueError:
            pass
    # all/all_time = no date filter

    if q and search_fields:
        query = Q()
        for field in search_fields:
            query |= Q(**{f'{field}__icontains': q})
        qs = qs.filter(query)
    return qs, {'date_filter': date_filter, 'start_date': start_date, 'end_date': end_date, 'q': q}


def _export_or_render(request, *, template='reports/detailed_report.html', title, active, headers, rows, summary_rows, filters, filename_slug, context=None):
    export = request.GET.get('export')
    generated_by = _display_user(request.user)
    if export in ('excel', 'pdf'):
        if export == 'pdf':
            return export_rows_to_pdf(
                headers, rows, f'{filename_slug}.pdf', title,
                date_filter=filters.get('date_filter'), start_date=filters.get('start_date'), end_date=filters.get('end_date'),
                generated_by=generated_by, summary_rows=summary_rows,
            )
        return export_rows_to_excel(
            headers, rows, f'{filename_slug}.xlsx', title[:31], title=title,
            date_filter=filters.get('date_filter'), start_date=filters.get('start_date'), end_date=filters.get('end_date'),
            generated_by=generated_by, summary_rows=summary_rows,
        )
    payload = {
        'title': title, 'active': active, 'headers': headers, 'rows': rows[:500],
        'summary_rows': summary_rows, 'date_range_label': _date_range_context(filters),
        'generated_by': generated_by, **filters,
    }
    if context:
        payload.update(context)
    return render(request, template, payload)


@role_required(*FINANCE_ROLES)
def revenue_dashboard(request):
    today = timezone.localdate()
    yesterday = today - datetime.timedelta(days=1)
    week_start = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    filter_applied = 'date_filter' in request.GET or request.GET.get('export') in ('excel', 'pdf')

    date_filter = request.GET.get('date_filter', 'all_time')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    visit_qs = Visit.objects.filter(payment_status=Visit.PaymentStatus.PAID)
    bill_qs = Bill.objects.filter(status=Bill.Status.PAID)
    pharmacy_qs = PharmacySale.objects.all()

    if date_filter == 'today':
        visit_qs = visit_qs.filter(visit_date=today)
        bill_qs = bill_qs.filter(created_at__date=today)
        pharmacy_qs = pharmacy_qs.filter(created_at__date=today)
    elif date_filter == 'yesterday':
        visit_qs = visit_qs.filter(visit_date=yesterday)
        bill_qs = bill_qs.filter(created_at__date=yesterday)
        pharmacy_qs = pharmacy_qs.filter(created_at__date=yesterday)
    elif date_filter in ('weekly', 'week'):
        visit_qs = visit_qs.filter(visit_date__gte=week_start)
        bill_qs = bill_qs.filter(created_at__date__gte=week_start)
        pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=week_start)
    elif date_filter in ('monthly', 'month'):
        visit_qs = visit_qs.filter(visit_date__gte=month_start)
        bill_qs = bill_qs.filter(created_at__date__gte=month_start)
        pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=month_start)
    elif date_filter in ('yearly', 'year'):
        visit_qs = visit_qs.filter(visit_date__gte=year_start)
        bill_qs = bill_qs.filter(created_at__date__gte=year_start)
        pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=year_start)
    elif date_filter == 'custom' and start_date_str:
        try:
            start_date = datetime.date.fromisoformat(start_date_str)
            end_date = datetime.date.fromisoformat(end_date_str) if end_date_str else None
            visit_qs = visit_qs.filter(visit_date__gte=start_date)
            bill_qs = bill_qs.filter(created_at__date__gte=start_date)
            pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=start_date)
            if end_date:
                visit_qs = visit_qs.filter(visit_date__lte=end_date)
                bill_qs = bill_qs.filter(created_at__date__lte=end_date)
                pharmacy_qs = pharmacy_qs.filter(created_at__date__lte=end_date)
        except ValueError:
            pass

    opd_total = visit_qs.aggregate(t=Sum('registration_fee'))['t'] or Decimal('0') if filter_applied else Decimal('0')
    bill_total = bill_qs.aggregate(t=Sum('total_amount'))['t'] or Decimal('0') if filter_applied else Decimal('0')
    pharmacy_total = pharmacy_qs.aggregate(t=Sum('total_amount'))['t'] or Decimal('0') if filter_applied else Decimal('0')
    grand_total = opd_total + bill_total + pharmacy_total

    if request.GET.get('export') in ('excel', 'pdf'):
        headers = ['Source', 'Record #', 'Patient', 'Type/Department', 'Payment Method', 'Amount', 'Date']
        rows = []
        for v in visit_qs.select_related('patient', 'department').order_by('-visit_date', '-id')[:5000]:
            rows.append(('OPD Registration', v.receipt_number, v.patient.full_name, v.department.name if v.department else '', v.get_payment_status_display(), v.registration_fee, v.visit_date))
        for b in bill_qs.select_related('patient').order_by('-created_at')[:5000]:
            rows.append(('Billing', b.bill_number, b.patient.full_name, b.get_bill_type_display(), b.get_payment_method_display(), b.total_amount, timezone.localtime(b.created_at).replace(tzinfo=None)))
        for s in pharmacy_qs.select_related('patient').order_by('-created_at')[:5000]:
            rows.append(('Pharmacy', s.sale_number, s.patient.full_name if s.patient else 'Walk-in', 'Pharmacy Sale', s.get_payment_method_display(), s.total_amount, timezone.localtime(s.created_at).replace(tzinfo=None)))
        return _export_or_render(request, title='Overall Hospital Revenue Report', active='overall_revenue', headers=headers, rows=rows, summary_rows=[('OPD Revenue', _money(opd_total)), ('Billing Revenue', _money(bill_total)), ('Pharmacy Revenue', _money(pharmacy_total)), ('Grand Total', _money(grand_total))], filters={'date_filter': date_filter, 'start_date': start_date_str, 'end_date': end_date_str, 'q': ''}, filename_slug='overall_hospital_revenue')

    todays_revenue = (Visit.objects.filter(visit_date=today, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0) + (Bill.objects.filter(created_at__date=today, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0) + (PharmacySale.objects.filter(created_at__date=today).aggregate(t=Sum('total_amount'))['t'] or 0) if filter_applied else 0
    monthly_revenue = (Visit.objects.filter(visit_date__gte=month_start, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0) + (Bill.objects.filter(created_at__date__gte=month_start, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0) + (PharmacySale.objects.filter(created_at__date__gte=month_start).aggregate(t=Sum('total_amount'))['t'] or 0) if filter_applied else 0
    yearly_revenue = (Visit.objects.filter(visit_date__gte=year_start, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0) + (Bill.objects.filter(created_at__date__gte=year_start, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0) + (PharmacySale.objects.filter(created_at__date__gte=year_start).aggregate(t=Sum('total_amount'))['t'] or 0) if filter_applied else 0
    total_revenue = (Visit.objects.filter(payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0) + (Bill.objects.filter(status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0) + (PharmacySale.objects.all().aggregate(t=Sum('total_amount'))['t'] or 0) if filter_applied else 0
    department_revenue = visit_qs.values('department__name').annotate(total=Sum('registration_fee'), visits=Count('id')).order_by('-total') if filter_applied else []
    return render(request, 'reports/revenue_dashboard.html', {
        'filter_applied': filter_applied, 'grand_total': grand_total, 'opd_total': opd_total, 'bill_total': bill_total, 'pharmacy_total': pharmacy_total,
        'opd_percent': (float(opd_total) / float(grand_total) * 100) if grand_total else 0,
        'bill_percent': (float(bill_total) / float(grand_total) * 100) if grand_total else 0,
        'pharmacy_percent': (float(pharmacy_total) / float(grand_total) * 100) if grand_total else 0,
        'todays_revenue': todays_revenue, 'monthly_revenue': monthly_revenue, 'yearly_revenue': yearly_revenue, 'total_revenue': total_revenue,
        'department_revenue': department_revenue, 'date_filter': date_filter, 'start_date': start_date_str, 'end_date': end_date_str,
    })


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD)
def registration_report(request):
    visits = Visit.objects.select_related('patient', 'department', 'doctor').all()
    if _is_department_head(request.user):
        visits = visits.filter(department=request.user.department)
    visits, filters = apply_report_filters(visits, request, 'visit_date', ['receipt_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'patient__phone_number', 'department__name'])
    headers = ['Receipt #', 'Patient', 'Patient ID', 'Phone', 'Date', 'Department', 'Doctor', 'Type', 'Fee']
    rows = [(v.receipt_number, v.patient.full_name, v.patient.patient_code, v.patient.phone_number, v.visit_date, v.department.name if v.department else '', v.doctor.full_name if v.doctor else '', v.get_patient_type_display(), v.registration_fee) for v in visits.order_by('-visit_date', '-id')[:5000]]
    return _export_or_render(request, title='Registration Report', active='registration', headers=headers, rows=rows, summary_rows=[('Total Visits', visits.count()), ('Total Registration Fees', _money(visits.aggregate(t=Sum('registration_fee'))['t']))], filters=filters, filename_slug='registration_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD)
def department_report(request):
    departments = Department.objects.annotate(visit_count=Count('visits'), doctor_count=Count('doctors', distinct=True), staff_count=Count('staff_users', distinct=True))
    if _is_department_head(request.user):
        departments = departments.filter(pk=request.user.department_id)
    q = request.GET.get('q', '').strip()
    if q:
        departments = departments.filter(name__icontains=q)
    filters = {'date_filter': request.GET.get('date_filter', 'all'), 'start_date': request.GET.get('start_date', ''), 'end_date': request.GET.get('end_date', ''), 'q': q}
    headers = ['Department', 'Visits', 'Doctors', 'Staff']
    rows = [(d.name, d.visit_count, d.doctor_count, d.staff_count) for d in departments.order_by('name')]
    return _export_or_render(request, title='Department Report', active='department', headers=headers, rows=rows, summary_rows=[('Departments', departments.count()), ('Total Visits', sum(r[1] for r in rows))], filters=filters, filename_slug='department_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD)
def doctor_report(request):
    doctors = Doctor.objects.annotate(visit_count=Count('visits')).select_related('department')
    if _is_department_head(request.user):
        doctors = doctors.filter(department=request.user.department)
    q = request.GET.get('q', '').strip()
    if q:
        doctors = doctors.filter(Q(full_name__icontains=q) | Q(department__name__icontains=q) | Q(specialization__icontains=q) | Q(qualification__icontains=q))
    filters = {'date_filter': request.GET.get('date_filter', 'all'), 'start_date': request.GET.get('start_date', ''), 'end_date': request.GET.get('end_date', ''), 'q': q}
    headers = ['Doctor', 'Department', 'Specialization', 'Qualification', 'Visits', 'Extension Service']
    rows = [(d.full_name, d.department.name if d.department else '', d.specialization, d.qualification, d.visit_count, 'Yes' if d.is_extension_service else 'No') for d in doctors.order_by('full_name')]
    return _export_or_render(request, title='Doctor Report', active='doctor', headers=headers, rows=rows, summary_rows=[('Doctors', doctors.count()), ('Total Visits', sum(r[4] for r in rows))], filters=filters, filename_slug='doctor_report')


@role_required(*FINANCE_ROLES)
def counter_report(request):
    bills = Bill.objects.select_related('cashier', 'patient').filter(status=Bill.Status.PAID)
    bills, filters = apply_report_filters(bills, request, 'created_at__date', ['bill_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'patient__phone_number', 'cashier__username', 'counter_name'])
    totals_by_method = {method: bills.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or 0 for method, _ in PaymentMethod.choices}
    headers = ['Bill #', 'Patient', 'Patient ID', 'Cashier', 'Counter', 'Method', 'Type', 'Total', 'Date']
    rows = [(b.bill_number, b.patient.full_name, b.patient.patient_code, b.cashier.username if b.cashier else '', b.counter_name, b.get_payment_method_display(), b.get_bill_type_display(), b.total_amount, timezone.localtime(b.created_at).replace(tzinfo=None)) for b in bills.order_by('-created_at')[:5000]]
    if request.GET.get('export') in ('excel', 'pdf'):
        return _export_or_render(request, title='Cash Counter Report', active='counter', headers=headers, rows=rows, summary_rows=[('Transactions', bills.count()), ('Grand Total', _money(bills.aggregate(t=Sum('total_amount'))['t']))], filters=filters, filename_slug='counter_report')
    return render(request, 'reports/counter_report.html', {'bills': bills.order_by('-created_at')[:500], 'by_cashier': bills.values('cashier__username').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'), 'totals_by_method': totals_by_method, **filters})


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.PHARMACY)
def pharmacy_report(request):
    sales = PharmacySale.objects.select_related('patient', 'sold_by').all()
    sales, filters = apply_report_filters(sales, request, 'created_at__date', ['sale_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'sold_by__username'])
    headers = ['Sale #', 'Patient', 'Patient ID', 'Method', 'Total', 'Sold By', 'Date']
    rows = [(s.sale_number, s.patient.full_name if s.patient else 'Walk-in', s.patient.patient_code if s.patient else '', s.get_payment_method_display(), s.total_amount, s.sold_by.username if s.sold_by else '', timezone.localtime(s.created_at).replace(tzinfo=None)) for s in sales.order_by('-created_at')[:5000]]
    return _export_or_render(request, title='Pharmacy Revenue Report', active='pharmacy', headers=headers, rows=rows, summary_rows=[('Sales', sales.count()), ('Grand Total', _money(sales.aggregate(t=Sum('total_amount'))['t']))], filters=filters, filename_slug='pharmacy_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.LABORATORY)
def laboratory_report(request):
    requests_qs = LabTestRequest.objects.select_related('consultation__visit__patient', 'patient')
    requests_qs, filters = apply_report_filters(requests_qs, request, 'requested_at__date', ['test_name', 'lab_code', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'consultation__visit__patient__patient_code'])
    headers = ['Lab Code', 'Test', 'Patient', 'Patient ID', 'Status', 'Requested At', 'Completed At']
    rows = [(r.lab_code, r.test_name, r.patient_obj.full_name if r.patient_obj else '', r.patient_obj.patient_code if r.patient_obj else '', r.get_status_display(), timezone.localtime(r.requested_at).replace(tzinfo=None), timezone.localtime(r.completed_at).replace(tzinfo=None) if r.completed_at else '') for r in requests_qs.order_by('-requested_at')[:5000]]
    return _export_or_render(request, title='Laboratory Operational Report', active='laboratory', headers=headers, rows=rows, summary_rows=[('Total Requests', requests_qs.count()), ('Pending', requests_qs.filter(status=RequestStatus.REQUESTED).count()), ('Completed', requests_qs.filter(status=RequestStatus.COMPLETED).count())], filters=filters, filename_slug='laboratory_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.RADIOLOGY)
def radiology_report(request):
    requests_qs = RadiologyRequest.objects.select_related('consultation__visit__patient', 'patient')
    requests_qs, filters = apply_report_filters(requests_qs, request, 'requested_at__date', ['radiology_number', 'custom_service_name', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'consultation__visit__patient__patient_code'])
    headers = ['Radiology #', 'Service', 'Patient', 'Patient ID', 'Status', 'Requested At', 'Completed At']
    rows = [(r.radiology_number, r.display_service_name, r.patient_obj.full_name if r.patient_obj else '', r.patient_obj.patient_code if r.patient_obj else '', r.get_status_display(), timezone.localtime(r.requested_at).replace(tzinfo=None), timezone.localtime(r.completed_at).replace(tzinfo=None) if r.completed_at else '') for r in requests_qs.order_by('-requested_at')[:5000]]
    return _export_or_render(request, title='Radiology Operational Report', active='radiology', headers=headers, rows=rows, summary_rows=[('Total Requests', requests_qs.count()), ('Pending', requests_qs.filter(status=RequestStatus.REQUESTED).count()), ('Completed', requests_qs.filter(status=RequestStatus.COMPLETED).count())], filters=filters, filename_slug='radiology_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.NURSING)
def nursing_report(request):
    from nursing.models import NursingNote
    notes = NursingNote.objects.select_related('admission__patient', 'recorded_by')
    notes, filters = apply_report_filters(notes, request, 'recorded_at__date', ['admission__patient__patient_code', 'admission__patient__first_name', 'admission__patient__last_name', 'recorded_by__username', 'content'])
    headers = ['Patient', 'Patient ID', 'Admission #', 'Note Type', 'Recorded By', 'Recorded At']
    rows = [(n.admission.patient.full_name, n.admission.patient.patient_code, n.admission.admission_number, n.get_note_type_display(), n.recorded_by.username if n.recorded_by else '', timezone.localtime(n.recorded_at).replace(tzinfo=None)) for n in notes.order_by('-recorded_at')[:5000]]
    return _export_or_render(request, title='Nursing Report', active='nursing', headers=headers, rows=rows, summary_rows=[('Total Notes', notes.count())], filters=filters, filename_slug='nursing_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.OPERATION_THEATRE)
def ot_report(request):
    from operation_theatre.models import Surgery
    surgeries = Surgery.objects.select_related('patient', 'surgeon')
    surgeries, filters = apply_report_filters(surgeries, request, 'scheduled_datetime__date', ['surgery_number', 'surgery_name', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'surgeon__full_name'])
    headers = ['Surgery #', 'Patient', 'Surgery', 'Surgeon', 'Status', 'Scheduled', 'Charge']
    rows = [(s.surgery_number, s.patient.full_name, s.surgery_name, s.surgeon.full_name if s.surgeon else '', s.get_status_display(), timezone.localtime(s.scheduled_datetime).replace(tzinfo=None) if s.scheduled_datetime else '', s.charge_amount) for s in surgeries.order_by('-scheduled_datetime')[:5000]]
    return _export_or_render(request, title='Operation Theatre Report', active='ot', headers=headers, rows=rows, summary_rows=[('Surgeries', surgeries.count()), ('Completed', surgeries.filter(status=Surgery.Status.COMPLETED).count()), ('Total Charges', _money(surgeries.aggregate(t=Sum('charge_amount'))['t']))], filters=filters, filename_slug='operation_theatre_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.BLOOD_BANK)
def blood_bank_report(request):
    from blood_bank.models import BloodUnit, BloodIssue
    units = BloodUnit.objects.all()
    units, filters = apply_report_filters(units, request, 'collection_date', ['bag_number', 'blood_group'])
    headers = ['Bag #', 'Group', 'Component', 'Qty (ml)', 'Status', 'Collected', 'Expires']
    rows = [(u.bag_number, u.blood_group, u.get_component_display(), u.quantity_ml, u.get_status_display(), u.collection_date, u.expiry_date) for u in units.order_by('-collection_date')[:5000]]
    return _export_or_render(request, title='Blood Bank Report', active='blood', headers=headers, rows=rows, summary_rows=[('Total Units', units.count()), ('Available', units.filter(status=BloodUnit.Status.AVAILABLE).count()), ('Issued Records', BloodIssue.objects.count())], filters=filters, filename_slug='blood_bank_report')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.WARD_ADMISSION)
def admission_report(request):
    from admissions.models import Admission, AdmissionDeposit
    admissions = Admission.objects.select_related('patient', 'department', 'ward', 'bed', 'admitting_doctor')
    admissions, filters = apply_report_filters(admissions, request, 'admission_date__date', ['admission_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'department__name', 'ward__name'])
    headers = ['Admission #', 'Patient', 'Patient ID', 'Department', 'Ward/Bed', 'Status', 'Admitted', 'Discharged', 'Estimated Charge']
    rows = [(a.admission_number, a.patient.full_name, a.patient.patient_code, a.department.name, f'{a.ward.name} / {a.bed.bed_number if a.bed else "-"}', a.get_status_display(), timezone.localtime(a.admission_date).replace(tzinfo=None), timezone.localtime(a.discharge_date).replace(tzinfo=None) if a.discharge_date else '', a.admission_charge_estimate) for a in admissions.order_by('-admission_date')[:5000]]
    deposits = AdmissionDeposit.objects.filter(admission__in=admissions)
    return _export_or_render(request, title='Admission Report', active='admission', headers=headers, rows=rows, summary_rows=[('Admissions', admissions.count()), ('Currently Admitted', admissions.filter(status=Admission.Status.ADMITTED).count()), ('Total Estimated Charges', _money(sum((r[8] for r in rows), Decimal('0')))), ('Deposits/Refunds/Usage Records', deposits.count())], filters=filters, filename_slug='admission_report')


@role_required(*FINANCE_ROLES)
def insurance_report(request):
    from insurance.models import InsuranceClaim
    claims = InsuranceClaim.objects.select_related('patient', 'insurance_company', 'submitted_by', 'reviewed_by')
    claims, filters = apply_report_filters(claims, request, 'submitted_at__date', ['claim_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'insurance_company__name'])
    headers = ['Claim #', 'Patient', 'Patient ID', 'Company', 'Status', 'Claimed', 'Approved', 'Patient Payable', 'Submitted']
    rows = [(c.claim_number, c.patient.full_name, c.patient.patient_code, c.insurance_company.name, c.get_status_display(), c.amount_claimed, c.approved_amount or 0, c.patient_payable_amount, timezone.localtime(c.submitted_at).replace(tzinfo=None)) for c in claims.order_by('-submitted_at')[:5000]]
    return _export_or_render(request, title='Insurance Report', active='insurance', headers=headers, rows=rows, summary_rows=[('Claims', claims.count()), ('Claimed Total', _money(claims.aggregate(t=Sum('amount_claimed'))['t'])), ('Approved Total', _money(claims.aggregate(t=Sum('approved_amount'))['t']))], filters=filters, filename_slug='insurance_report')


@role_required(*FINANCE_ROLES)
def finance_report(request):
    bills = Bill.objects.select_related('patient', 'cashier').filter(status=Bill.Status.PAID)
    bills, filters = apply_report_filters(bills, request, 'created_at__date', ['bill_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'cashier__username', 'counter_name'])
    headers = ['Bill #', 'Patient', 'Bill Type', 'Counter', 'Cashier', 'Method', 'Gross', 'Staff Discount', 'Insurance', 'Net Paid', 'Date']
    rows = [(b.bill_number, b.patient.full_name, b.get_bill_type_display(), b.counter_name, b.cashier.username if b.cashier else '', b.get_payment_method_display(), b.total_amount, b.staff_discount_amount, b.insurance_coverage_amount, b.final_amount_paid, timezone.localtime(b.created_at).replace(tzinfo=None)) for b in bills.order_by('-created_at')[:5000]]
    return _export_or_render(request, title='Finance Billing Report', active='finance', headers=headers, rows=rows, summary_rows=[('Bills', bills.count()), ('Gross Total', _money(bills.aggregate(t=Sum('total_amount'))['t'])), ('Staff Discounts', _money(bills.aggregate(t=Sum('staff_discount_amount'))['t'])), ('Insurance Coverage', _money(bills.aggregate(t=Sum('insurance_coverage_amount'))['t']))], filters=filters, filename_slug='finance_report')


@role_required(*FINANCE_ROLES)
def department_wise_revenue_report(request):
    visits = Visit.objects.filter(payment_status=Visit.PaymentStatus.PAID)
    visits, filters = apply_report_filters(visits, request, 'visit_date', ['department__name'])
    rows_data = visits.values('department__name').annotate(visits=Count('id'), total=Sum('registration_fee')).order_by('-total')
    headers = ['Department', 'Visits', 'Registration Revenue']
    rows = [(r['department__name'] or 'Unknown', r['visits'], r['total'] or 0) for r in rows_data]
    return _export_or_render(request, title='Department-wise Revenue Report', active='department_revenue', headers=headers, rows=rows, summary_rows=[('Departments', len(rows)), ('Total OPD Revenue', _money(sum((r[2] for r in rows), Decimal('0'))))], filters=filters, filename_slug='department_wise_revenue_report')


@role_required(*FINANCE_ROLES)
def staff_attendance_report(request):
    records = StaffAttendance.objects.select_related('staff', 'staff__department')
    records, filters = apply_report_filters(records, request, 'date', ['staff__staff_id', 'staff__first_name', 'staff__last_name', 'staff__username', 'staff__department__name', 'status'])
    headers = ['Date', 'Staff ID', 'Staff Name', 'Department', 'Check In', 'Check Out', 'Hours', 'Status', 'Source']
    rows = [(r.date, r.staff.staff_id, r.staff.get_full_name() or r.staff.username, r.staff.department.name if r.staff.department else '', timezone.localtime(r.check_in).replace(tzinfo=None) if r.check_in else '', timezone.localtime(r.check_out).replace(tzinfo=None) if r.check_out else '', r.total_working_hours, r.get_status_display(), r.source) for r in records.order_by('-date', 'staff__first_name')[:5000]]
    return _export_or_render(request, title='Staff Attendance History Report', active='staff_attendance', headers=headers, rows=rows, summary_rows=[('Records', records.count()), ('Present', records.filter(status=StaffAttendance.Status.PRESENT).count()), ('Leave', records.filter(status=StaffAttendance.Status.LEAVE).count()), ('Absent', records.filter(status=StaffAttendance.Status.ABSENT).count())], filters=filters, filename_slug='staff_attendance_report')


@role_required(*FINANCE_ROLES)
def staff_leave_report(request):
    leaves = StaffLeaveRequest.objects.select_related('staff', 'staff__department', 'reviewed_by')
    leaves, filters = apply_report_filters(leaves, request, 'start_date', ['staff__staff_id', 'staff__first_name', 'staff__last_name', 'staff__department__name', 'leave_type', 'status'])
    headers = ['Staff ID', 'Staff Name', 'Department', 'Leave Type', 'From', 'To', 'Days', 'Status', 'Reviewed By']
    rows = [(l.staff.staff_id, l.staff.get_full_name() or l.staff.username, l.staff.department.name if l.staff.department else '', l.leave_type, l.start_date, l.end_date, l.total_days, l.get_status_display(), l.reviewed_by.username if l.reviewed_by else '') for l in leaves.order_by('-start_date')[:5000]]
    return _export_or_render(request, title='Staff Leave History Report', active='staff_leave', headers=headers, rows=rows, summary_rows=[('Leave Requests', leaves.count()), ('Approved', leaves.filter(status=StaffLeaveRequest.Status.APPROVED).count()), ('Pending', leaves.filter(status=StaffLeaveRequest.Status.PENDING).count())], filters=filters, filename_slug='staff_leave_report')


@role_required(*FINANCE_ROLES)
def payroll_report(request):
    payments = StaffSalaryPayment.objects.select_related('staff', 'staff__department', 'prepared_by')
    # Salary reports are monthly records; created_at is still used for Today/Week/Custom export audit range filtering.
    payments, filters = apply_report_filters(payments, request, 'created_at__date', ['staff__staff_id', 'staff__first_name', 'staff__last_name', 'staff__department__name', 'status'])
    headers = ['Year', 'Month', 'Staff ID', 'Staff Name', 'Department', 'Present', 'Half Day', 'Leave', 'Absent', 'Base', 'Bonus', 'Deduction', 'Net', 'Status', 'Paid At']
    rows = [(p.year, p.month, p.staff.staff_id, p.staff.get_full_name() or p.staff.username, p.staff.department.name if p.staff.department else '', p.present_days, p.half_days, p.leave_days, p.absent_days, p.base_amount, p.bonus_amount, p.deductions, p.net_amount, p.get_status_display(), timezone.localtime(p.paid_at).replace(tzinfo=None) if p.paid_at else '') for p in payments.order_by('-year', '-month', 'staff__first_name')[:5000]]
    return _export_or_render(request, title='Payroll / Salary Payment Report', active='payroll', headers=headers, rows=rows, summary_rows=[('Salary Records', payments.count()), ('Net Payroll Total', _money(payments.aggregate(t=Sum('net_amount'))['t'])), ('Paid Records', payments.filter(status=StaffSalaryPayment.Status.PAID).count())], filters=filters, filename_slug='payroll_report')


@role_required(*FINANCE_ROLES)
def staff_department_report(request):
    staff = User.objects.select_related('department').exclude(role=Role.SUPER_ADMIN)
    q = request.GET.get('q', '').strip()
    if q:
        staff = staff.filter(Q(staff_id__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q) | Q(department__name__icontains=q) | Q(designation__icontains=q))
    filters = {'date_filter': request.GET.get('date_filter', 'all'), 'start_date': request.GET.get('start_date', ''), 'end_date': request.GET.get('end_date', ''), 'q': q}
    headers = ['Staff ID', 'Name', 'Username', 'Role', 'Department', 'Designation', 'Department Head', 'Active']
    rows = [(s.staff_id, s.get_full_name() or s.username, s.username, s.get_role_display(), s.department.name if s.department else '', s.designation, 'Yes' if s.is_department_head else 'No', 'Yes' if s.is_active_staff else 'No') for s in staff.order_by('department__name', 'first_name')[:5000]]
    return _export_or_render(request, title='Department-wise Staff Report', active='staff_department', headers=headers, rows=rows, summary_rows=[('Staff Records', staff.count()), ('Active Staff', staff.filter(is_active_staff=True).count()), ('Department Heads', staff.filter(is_department_head=True).count())], filters=filters, filename_slug='department_wise_staff_report')
