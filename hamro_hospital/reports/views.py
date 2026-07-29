import datetime

from django.db.models import Sum, Count, Q
from django.shortcuts import render

from accounts.decorators import super_admin_required, role_required
from accounts.models import Role
from billing.models import Bill, PaymentMethod
from pharmacy.models import PharmacySale
from patients.models import Visit, Patient
from departments.models import Department
from doctors.models import Doctor
from consultations.models import LabTestRequest, RequestStatus
from reports.excel_utils import export_rows_to_excel, export_rows_to_pdf


def apply_report_filters(qs, request, date_field, search_fields=None):
    """Shared date/search filtering for finance reports."""
    today = datetime.date.today()
    date_filter = request.GET.get('date_filter', 'today')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    q = request.GET.get('q', '').strip()

    if date_filter == 'today':
        qs = qs.filter(**{date_field: today})
    elif date_filter == 'yesterday':
        qs = qs.filter(**{date_field: today - datetime.timedelta(days=1)})
    elif date_filter in ('last_7', '7_days'):
        qs = qs.filter(**{f'{date_field}__gte': today - datetime.timedelta(days=7)})
    elif date_filter in ('last_30', '30_days'):
        qs = qs.filter(**{f'{date_field}__gte': today - datetime.timedelta(days=30)})
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
    # all = no date filter

    if q and search_fields:
        query = Q()
        for field in search_fields:
            query |= Q(**{f'{field}__icontains': q})
        qs = qs.filter(query)
    return qs, {'date_filter': date_filter, 'start_date': start_date, 'end_date': end_date, 'q': q}


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def revenue_dashboard(request):
    import datetime
    from django.utils import timezone
    from django.db.models import Sum

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    week_start = today - datetime.timedelta(days=today.weekday()) # Monday of this week
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # Cards should stay blank until the Super Admin actually applies a filter,
    # not just on first page load with an implicit "all_time" default.
    filter_applied = 'date_filter' in request.GET

    # Preset filters
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
            if end_date_str:
                end_date = datetime.date.fromisoformat(end_date_str)
                visit_qs = visit_qs.filter(visit_date__range=[start_date, end_date])
                bill_qs = bill_qs.filter(created_at__date__range=[start_date, end_date])
                pharmacy_qs = pharmacy_qs.filter(created_at__date__range=[start_date, end_date])
            else:
                visit_qs = visit_qs.filter(visit_date__gte=start_date)
                bill_qs = bill_qs.filter(created_at__date__gte=start_date)
                pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=start_date)
        except ValueError:
            pass

    # Sum aggregations
    if filter_applied:
        opd_total = visit_qs.aggregate(t=Sum('registration_fee'))['t'] or 0
        bill_total = bill_qs.aggregate(t=Sum('total_amount'))['t'] or 0
        pharmacy_total = pharmacy_qs.aggregate(t=Sum('total_amount'))['t'] or 0
        grand_total = opd_total + bill_total + pharmacy_total

        todays_revenue = (
            Visit.objects.filter(visit_date=today, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0
        ) + (
            Bill.objects.filter(created_at__date=today, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0
        ) + (
            PharmacySale.objects.filter(created_at__date=today).aggregate(t=Sum('total_amount'))['t'] or 0
        )

        monthly_revenue = (
            Visit.objects.filter(visit_date__gte=month_start, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0
        ) + (
            Bill.objects.filter(created_at__date__gte=month_start, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0
        ) + (
            PharmacySale.objects.filter(created_at__date__gte=month_start).aggregate(t=Sum('total_amount'))['t'] or 0
        )

        yearly_revenue = (
            Visit.objects.filter(visit_date__gte=year_start, payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0
        ) + (
            Bill.objects.filter(created_at__date__gte=year_start, status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0
        ) + (
            PharmacySale.objects.filter(created_at__date__gte=year_start).aggregate(t=Sum('total_amount'))['t'] or 0
        )

        total_revenue = (
            Visit.objects.filter(payment_status=Visit.PaymentStatus.PAID).aggregate(t=Sum('registration_fee'))['t'] or 0
        ) + (
            Bill.objects.filter(status=Bill.Status.PAID).aggregate(t=Sum('total_amount'))['t'] or 0
        ) + (
            PharmacySale.objects.all().aggregate(t=Sum('total_amount'))['t'] or 0
        )

        opd_percent = (float(opd_total) / float(grand_total) * 100) if grand_total > 0 else 0
        bill_percent = (float(bill_total) / float(grand_total) * 100) if grand_total > 0 else 0
        pharmacy_percent = (float(pharmacy_total) / float(grand_total) * 100) if grand_total > 0 else 0
        department_revenue = visit_qs.values('department__name').annotate(total=Sum('registration_fee'), visits=Count('id')).order_by('-total')
    else:
        opd_total = bill_total = pharmacy_total = grand_total = 0
        todays_revenue = monthly_revenue = yearly_revenue = total_revenue = 0
        opd_percent = bill_percent = pharmacy_percent = 0
        department_revenue = []

    return render(request, 'reports/revenue_dashboard.html', {
        'filter_applied': filter_applied,
        'grand_total': grand_total,
        'opd_total': opd_total,
        'bill_total': bill_total,
        'pharmacy_total': pharmacy_total,
        
        'opd_percent': opd_percent,
        'bill_percent': bill_percent,
        'pharmacy_percent': pharmacy_percent,
        
        'todays_revenue': todays_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'total_revenue': total_revenue,
        'department_revenue': department_revenue,
        
        'date_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
    })


@super_admin_required
def registration_report(request):
    visits = Visit.objects.select_related('patient', 'department').all()
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')
    if date_from:
        visits = visits.filter(visit_date__gte=date_from)
    if date_to:
        visits = visits.filter(visit_date__lte=date_to)

    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Receipt #', 'Patient', 'Patient ID', 'Date', 'Department', 'Type', 'Fee']
        rows = [(v.receipt_number, v.patient.full_name, v.patient.patient_code, v.visit_date, v.department.name, v.get_patient_type_display(), v.registration_fee) for v in visits[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'registration_report.pdf', 'Registration Report')
        return export_rows_to_excel(headers, rows, 'registration_report.xlsx', 'Registrations')

    return render(request, 'reports/registration_report.html', {
        'visits': visits[:500], 'date_from': date_from, 'date_to': date_to,
        'total_fees': visits.aggregate(t=Sum('registration_fee'))['t'] or 0,
        'total_new_patients': Patient.objects.count(),
    })


@super_admin_required
def department_report(request):
    departments = Department.objects.annotate(
        visit_count=Count('visits'), doctor_count=Count('doctors', distinct=True),
    )
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Department', 'Visit Count', 'Doctor Count']
        rows = [(d.name, d.visit_count, d.doctor_count) for d in departments]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'department_report.pdf', 'Department Report')
        return export_rows_to_excel(headers, rows, 'department_report.xlsx', 'Departments')
    return render(request, 'reports/department_report.html', {'departments': departments})


@super_admin_required
def doctor_report(request):
    doctors = Doctor.objects.annotate(visit_count=Count('visits')).select_related('department')
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Doctor', 'Department', 'Visit Count']
        rows = [(d.full_name, d.department.name, d.visit_count) for d in doctors]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'doctor_report.pdf', 'Doctor Report')
        return export_rows_to_excel(headers, rows, 'doctor_report.xlsx', 'Doctors')
    return render(request, 'reports/doctor_report.html', {'doctors': doctors})


@super_admin_required
def counter_report(request):
    """Cash Counter collections broken down by cashier and payment method."""
    bills = Bill.objects.select_related('cashier', 'patient').filter(status=Bill.Status.PAID)
    bills, filter_context = apply_report_filters(
        bills, request, 'created_at__date', ['bill_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'cashier__username']
    )
    by_cashier = bills.values('cashier__username').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total')
    totals_by_method = {method: bills.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or 0 for method, _ in PaymentMethod.choices}
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Bill #', 'Patient', 'Cashier', 'Method', 'Total', 'Date']
        rows = [(b.bill_number, b.patient.full_name, b.cashier.username if b.cashier else '', b.get_payment_method_display(), b.total_amount, b.created_at.replace(tzinfo=None)) for b in bills[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'counter_report.pdf', 'Cash Counter Report')
        return export_rows_to_excel(headers, rows, 'counter_report.xlsx', 'Cash Counter')
    return render(request, 'reports/counter_report.html', {'bills': bills.order_by('-created_at')[:500], 'by_cashier': by_cashier, 'totals_by_method': totals_by_method, **filter_context})

@super_admin_required
def pharmacy_report(request):
    sales = PharmacySale.objects.select_related('patient', 'sold_by').all()
    sales, filter_context = apply_report_filters(sales, request, 'created_at__date', ['sale_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'sold_by__username'])
    totals_by_method = {method: sales.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or 0 for method, _ in PharmacySale.PaymentMethod.choices}
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Sale #', 'Patient', 'Method', 'Total', 'Date']
        rows = [(s.sale_number, s.patient.full_name if s.patient else 'Walk-in', s.get_payment_method_display(), s.total_amount, s.created_at.replace(tzinfo=None)) for s in sales[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'pharmacy_report.pdf', 'Pharmacy Report')
        return export_rows_to_excel(headers, rows, 'pharmacy_report.xlsx', 'Pharmacy')
    return render(request, 'reports/pharmacy_report.html', {'sales': sales.order_by('-created_at')[:500], 'total_sales': sales.count(), 'total_revenue': sales.aggregate(t=Sum('total_amount'))['t'] or 0, 'totals_by_method': totals_by_method, **filter_context})

@super_admin_required
def laboratory_report(request):
    requests_qs = LabTestRequest.objects.select_related('consultation__visit__patient', 'patient')
    requests_qs, filter_context = apply_report_filters(requests_qs, request, 'requested_at__date', ['test_name', 'lab_code', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'consultation__visit__patient__patient_code'])
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Test', 'Patient', 'Status', 'Requested At']
        rows = [(r.test_name, r.patient_obj.full_name, r.get_status_display(), r.requested_at.replace(tzinfo=None)) for r in requests_qs[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'laboratory_report.pdf', 'Laboratory Report')
        return export_rows_to_excel(headers, rows, 'laboratory_report.xlsx', 'Laboratory')
    return render(request, 'reports/laboratory_report.html', {'requests': requests_qs.order_by('-requested_at')[:500], 'total_requests': requests_qs.count(), 'pending': requests_qs.filter(status=RequestStatus.REQUESTED).count(), 'in_progress': requests_qs.filter(status=RequestStatus.IN_PROGRESS).count(), 'completed': requests_qs.filter(status=RequestStatus.COMPLETED).count(), **filter_context})

@super_admin_required
def nursing_report(request):
    from nursing.models import NursingNote
    notes = NursingNote.objects.select_related('admission__patient', 'recorded_by')
    notes, filter_context = apply_report_filters(notes, request, 'recorded_at__date', ['admission__patient__patient_code', 'admission__patient__first_name', 'admission__patient__last_name', 'recorded_by__username', 'content'])
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Patient', 'Note Type', 'Recorded By', 'Recorded At']
        rows = [(n.admission.patient.full_name, n.get_note_type_display(), n.recorded_by.username if n.recorded_by else '', n.recorded_at.replace(tzinfo=None)) for n in notes[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'nursing_report.pdf', 'Nursing Report')
        return export_rows_to_excel(headers, rows, 'nursing_report.xlsx', 'Nursing')
    return render(request, 'reports/nursing_report.html', {'notes': notes.order_by('-recorded_at')[:500], 'total_notes': notes.count(), **filter_context})

@super_admin_required
def ot_report(request):
    from operation_theatre.models import Surgery
    surgeries = Surgery.objects.select_related('patient', 'surgeon')
    surgeries, filter_context = apply_report_filters(surgeries, request, 'scheduled_datetime__date', ['surgery_number', 'surgery_name', 'patient__patient_code', 'patient__first_name', 'patient__last_name', 'surgeon__full_name'])
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Surgery #', 'Patient', 'Surgery', 'Surgeon', 'Status', 'Scheduled', 'Charge']
        rows = [(s.surgery_number, s.patient.full_name, s.surgery_name, s.surgeon.full_name, s.get_status_display(), s.scheduled_datetime.replace(tzinfo=None) if s.scheduled_datetime else '', s.charge_amount) for s in surgeries[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'ot_report.pdf', 'Operation Theatre Report')
        return export_rows_to_excel(headers, rows, 'ot_report.xlsx', 'Operation Theatre')
    return render(request, 'reports/ot_report.html', {'surgeries': surgeries.order_by('-scheduled_datetime')[:500], 'total_surgeries': surgeries.count(), 'completed': surgeries.filter(status=Surgery.Status.COMPLETED).count(), 'total_charges': surgeries.aggregate(t=Sum('charge_amount'))['t'] or 0, **filter_context})

@super_admin_required
def blood_bank_report(request):
    from blood_bank.models import BloodUnit, BloodIssue
    units = BloodUnit.objects.all()
    units, filter_context = apply_report_filters(units, request, 'collection_date', ['bag_number', 'blood_group'])
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Bag #', 'Group', 'Component', 'Qty (ml)', 'Status', 'Collected', 'Expires']
        rows = [(u.bag_number, u.blood_group, u.get_component_display(), u.quantity_ml, u.get_status_display(), u.collection_date, u.expiry_date) for u in units[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'blood_bank_report.pdf', 'Blood Bank Report')
        return export_rows_to_excel(headers, rows, 'blood_bank_report.xlsx', 'Blood Bank')
    return render(request, 'reports/blood_bank_report.html', {'units': units.order_by('-collection_date')[:500], 'total_units': units.count(), 'available': units.filter(status=BloodUnit.Status.AVAILABLE).count(), 'issued_total': BloodIssue.objects.count(), **filter_context})