import datetime

from django.db.models import Sum, Count
from django.shortcuts import render

from accounts.decorators import super_admin_required, role_required
from accounts.models import Role
from billing.models import Bill, PaymentMethod
from pharmacy.models import PharmacySale
from patients.models import Visit, Patient
from departments.models import Department
from doctors.models import Doctor
from consultations.models import LabTestRequest, RequestStatus
from reports.excel_utils import export_rows_to_excel


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
    elif date_filter == 'weekly':
        visit_qs = visit_qs.filter(visit_date__gte=week_start)
        bill_qs = bill_qs.filter(created_at__date__gte=week_start)
        pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=week_start)
    elif date_filter == 'monthly':
        visit_qs = visit_qs.filter(visit_date__gte=month_start)
        bill_qs = bill_qs.filter(created_at__date__gte=month_start)
        pharmacy_qs = pharmacy_qs.filter(created_at__date__gte=month_start)
    elif date_filter == 'yearly':
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
    else:
        opd_total = bill_total = pharmacy_total = grand_total = 0
        todays_revenue = monthly_revenue = yearly_revenue = total_revenue = 0
        opd_percent = bill_percent = pharmacy_percent = 0

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

    if request.GET.get('export') == 'excel':
        rows = [
            (v.receipt_number, v.patient.full_name, v.patient.patient_code, v.visit_date.replace(tzinfo=None) if hasattr(v.visit_date, 'replace') else v.visit_date,
             v.department.name, v.get_patient_type_display(), v.registration_fee)
            for v in visits
        ]
        return export_rows_to_excel(
            ['Receipt #', 'Patient', 'Patient ID', 'Date', 'Department', 'Type', 'Fee'],
            rows, 'registration_report.xlsx', 'Registrations',
        )

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
    if request.GET.get('export') == 'excel':
        rows = [(d.name, d.visit_count, d.doctor_count) for d in departments]
        return export_rows_to_excel(
            ['Department', 'Visit Count', 'Doctor Count'], rows, 'department_report.xlsx', 'Departments',
        )
    return render(request, 'reports/department_report.html', {'departments': departments})


@super_admin_required
def doctor_report(request):
    doctors = Doctor.objects.annotate(visit_count=Count('visits')).select_related('department')
    if request.GET.get('export') == 'excel':
        rows = [(d.full_name, d.department.name, d.visit_count) for d in doctors]
        return export_rows_to_excel(
            ['Doctor', 'Department', 'Visit Count'], rows, 'doctor_report.xlsx', 'Doctors',
        )
    return render(request, 'reports/doctor_report.html', {'doctors': doctors})


@super_admin_required
def counter_report(request):
    """Cash Counter collections broken down by cashier and payment method."""
    bills = Bill.objects.select_related('cashier').all()
    by_cashier = bills.values('cashier__username').annotate(
        total=Sum('total_amount'), count=Count('id'),
    ).order_by('-total')
    totals_by_method = {
        method: bills.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or 0
        for method, _ in PaymentMethod.choices
    }
    if request.GET.get('export') == 'excel':
        rows = [(r['cashier__username'], r['count'], r['total']) for r in by_cashier]
        return export_rows_to_excel(
            ['Cashier', 'Bill Count', 'Total Collected'], rows, 'counter_report.xlsx', 'Cash Counter',
        )
    return render(request, 'reports/counter_report.html', {
        'by_cashier': by_cashier, 'totals_by_method': totals_by_method,
    })


@super_admin_required
def pharmacy_report(request):
    sales = PharmacySale.objects.all()
    totals_by_method = {
        method: sales.filter(payment_method=method).aggregate(t=Sum('total_amount'))['t'] or 0
        for method, _ in PharmacySale.PaymentMethod.choices
    }
    if request.GET.get('export') == 'excel':
        rows = [(method, total) for method, total in totals_by_method.items()]
        return export_rows_to_excel(
            ['Payment Method', 'Total'], rows, 'pharmacy_report.xlsx', 'Pharmacy',
        )
    return render(request, 'reports/pharmacy_report.html', {
        'total_sales': sales.count(),
        'total_revenue': sales.aggregate(t=Sum('total_amount'))['t'] or 0,
        'totals_by_method': totals_by_method,
    })


@super_admin_required
def laboratory_report(request):
    requests_qs = LabTestRequest.objects.select_related('consultation__visit__patient')
    if request.GET.get('export') == 'excel':
        rows = [
            (r.test_name, r.patient_obj.full_name, r.get_status_display(), r.requested_at.replace(tzinfo=None))
            for r in requests_qs
        ]
        return export_rows_to_excel(
            ['Test', 'Patient', 'Status', 'Requested At'], rows, 'laboratory_report.xlsx', 'Laboratory',
        )
    return render(request, 'reports/laboratory_report.html', {
        'total_requests': requests_qs.count(),
        'pending': requests_qs.filter(status=RequestStatus.REQUESTED).count(),
        'in_progress': requests_qs.filter(status=RequestStatus.IN_PROGRESS).count(),
        'completed': requests_qs.filter(status=RequestStatus.COMPLETED).count(),
    })


@super_admin_required
def nursing_report(request):
    from nursing.models import NursingNote
    notes = NursingNote.objects.select_related('admission__patient', 'recorded_by')
    if request.GET.get('export') == 'excel':
        rows = [
            (n.admission.patient.full_name, n.get_note_type_display(),
             n.recorded_by.username if n.recorded_by else '', n.recorded_at.replace(tzinfo=None))
            for n in notes
        ]
        return export_rows_to_excel(
            ['Patient', 'Note Type', 'Recorded By', 'Recorded At'], rows, 'nursing_report.xlsx', 'Nursing',
        )
    return render(request, 'reports/nursing_report.html', {'total_notes': notes.count()})


@super_admin_required
def ot_report(request):
    from operation_theatre.models import Surgery
    surgeries = Surgery.objects.select_related('patient', 'surgeon')
    if request.GET.get('export') == 'excel':
        rows = [
            (s.surgery_number, s.patient.full_name, s.surgery_name, s.surgeon.full_name,
             s.get_status_display(), s.scheduled_datetime.replace(tzinfo=None) if s.scheduled_datetime else '', s.charge_amount)
            for s in surgeries
        ]
        return export_rows_to_excel(
            ['Surgery #', 'Patient', 'Surgery', 'Surgeon', 'Status', 'Scheduled', 'Charge'],
            rows, 'ot_report.xlsx', 'Operation Theatre',
        )
    return render(request, 'reports/ot_report.html', {
        'total_surgeries': surgeries.count(),
        'completed': surgeries.filter(status=Surgery.Status.COMPLETED).count(),
    })


@super_admin_required
def blood_bank_report(request):
    from blood_bank.models import BloodUnit, BloodIssue
    units = BloodUnit.objects.all()
    if request.GET.get('export') == 'excel':
        rows = [
            (u.bag_number, u.blood_group, u.get_component_display(), u.quantity_ml,
             u.get_status_display(), u.collection_date.replace(tzinfo=None) if u.collection_date else '', u.expiry_date.replace(tzinfo=None) if u.expiry_date else '')
            for u in units
        ]
        return export_rows_to_excel(
            ['Bag #', 'Group', 'Component', 'Qty (ml)', 'Status', 'Collected', 'Expires'],
            rows, 'blood_bank_report.xlsx', 'Blood Bank',
        )
    return render(request, 'reports/blood_bank_report.html', {
        'total_units': units.count(),
        'available': units.filter(status=BloodUnit.Status.AVAILABLE).count(),
        'issued_total': BloodIssue.objects.count(),
    })
