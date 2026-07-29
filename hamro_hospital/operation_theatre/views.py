import datetime

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import operation_theatre_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from documents.models import PatientDocument, DocumentCategory
from operation_theatre.forms import SurgeryScheduleForm, SurgeryUpdateForm
from operation_theatre.models import Surgery, OperationType
from patients.models import Patient


@operation_theatre_required
def dashboard_details(request):
    metric = request.GET.get('metric', 'scheduled')
    today = timezone.localdate()
    surgeries = Surgery.objects.select_related('patient', 'surgeon', 'ot_room', 'admission', 'surgeon__department')
    title = 'Operation Theatre Details'
    if metric == 'current':
        surgeries = surgeries.filter(status=Surgery.Status.IN_PROGRESS); title = 'Current Operations'
    elif metric == 'scheduled':
        surgeries = surgeries.filter(status=Surgery.Status.SCHEDULED, scheduled_datetime__gte=timezone.now() - datetime.timedelta(hours=24)); title = 'Scheduled Operations - Latest 24 Hours'
    elif metric == 'completed':
        surgeries = surgeries.filter(status=Surgery.Status.COMPLETED, completed_at__gte=timezone.now() - datetime.timedelta(hours=24)); title = 'Completed Operations - Latest 24 Hours'
    elif metric == 'revenue':
        surgeries = surgeries.none(); title = 'Operation Theater Revenue'
    q = (request.GET.get('q') or '').strip()
    date_filter = request.GET.get('date_filter','')
    start_date = request.GET.get('start_date','')
    end_date = request.GET.get('end_date','')
    if q:
        surgeries = surgeries.filter(Q(surgery_number__icontains=q)|Q(patient__patient_code__icontains=q)|Q(patient__first_name__icontains=q)|Q(patient__last_name__icontains=q)|Q(patient__phone_number__icontains=q)|Q(surgery_name__icontains=q)|Q(surgeon__full_name__icontains=q))
    if date_filter or start_date or end_date:
        if date_filter == 'today': surgeries = surgeries.filter(scheduled_datetime__date=today)
        elif date_filter == 'week': surgeries = surgeries.filter(scheduled_datetime__date__gte=today - datetime.timedelta(days=today.weekday()))
        elif date_filter == 'month': surgeries = surgeries.filter(scheduled_datetime__date__gte=today.replace(day=1))
        elif date_filter == 'year': surgeries = surgeries.filter(scheduled_datetime__date__gte=today.replace(month=1, day=1))
        try:
            if start_date: surgeries = surgeries.filter(scheduled_datetime__date__gte=datetime.date.fromisoformat(start_date))
            if end_date: surgeries = surgeries.filter(scheduled_datetime__date__lte=datetime.date.fromisoformat(end_date))
        except ValueError: pass
    from billing.models import Bill
    revenue_bills = Bill.objects.filter(bill_type='surgery', status=Bill.Status.PAID).select_related('patient')
    if metric == 'revenue':
        if date_filter == 'today': revenue_bills = revenue_bills.filter(created_at__date=today)
        elif date_filter == 'week': revenue_bills = revenue_bills.filter(created_at__date__gte=today - datetime.timedelta(days=today.weekday()))
        elif date_filter == 'month' or not date_filter: revenue_bills = revenue_bills.filter(created_at__date__gte=today.replace(day=1))
        elif date_filter == 'year': revenue_bills = revenue_bills.filter(created_at__date__gte=today.replace(month=1, day=1))
        try:
            if start_date: revenue_bills = revenue_bills.filter(created_at__date__gte=datetime.date.fromisoformat(start_date))
            if end_date: revenue_bills = revenue_bills.filter(created_at__date__lte=datetime.date.fromisoformat(end_date))
        except ValueError: pass
        if q: revenue_bills = revenue_bills.filter(Q(bill_number__icontains=q)|Q(patient__patient_code__icontains=q)|Q(patient__first_name__icontains=q)|Q(patient__last_name__icontains=q))
    return render(request, 'operation_theatre/dashboard_details.html', {'title': title, 'metric': metric, 'surgeries': surgeries.order_by('-scheduled_datetime')[:1000], 'revenue_bills': revenue_bills.order_by('-created_at')[:1000], 'revenue_total': revenue_bills.aggregate(t=Sum('total_amount'))['t'] or 0, 'q': q, 'date_filter': date_filter, 'start_date': start_date, 'end_date': end_date})


@operation_theatre_required
def ot_payment(request, patient_id):
    return redirect(f"{reverse('billing:create_bill', args=[patient_id])}?bill_type=surgery")


@operation_theatre_required
def patient_lookup(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'operation_theatre/patient_lookup.html', {'q': q, 'patients': patients})


@operation_theatre_required
def dashboard(request):
    today = datetime.date.today()
    window_start = timezone.now() - datetime.timedelta(hours=24)
    scheduled = Surgery.objects.filter(status=Surgery.Status.SCHEDULED).select_related('patient', 'surgeon')
    today_list = scheduled.filter(scheduled_datetime__gte=window_start)
    in_progress = Surgery.objects.filter(status=Surgery.Status.IN_PROGRESS).select_related('patient', 'surgeon')
    completed_today = Surgery.objects.filter(status=Surgery.Status.COMPLETED, completed_at__gte=window_start)
    recent_uploads = PatientDocument.objects.filter(
        category__in=[DocumentCategory.OPERATION_RECORD, DocumentCategory.CONSENT_FORM],
    ).select_related('patient', 'uploaded_by').order_by('-uploaded_at')[:10]

    from billing.models import Bill
    todays_revenue = Bill.objects.filter(bill_type='surgery', status=Bill.Status.PAID, created_at__gte=window_start).aggregate(t=Sum('total_amount'))['t'] or 0
    ot_payments = Bill.objects.filter(bill_type='surgery').exclude(status=Bill.Status.CANCELLED).select_related('patient').order_by('-created_at')[:10]

    return render(request, 'operation_theatre/dashboard.html', {
        'today_list': today_list, 'in_progress': in_progress,
        'scheduled_count': scheduled.count(), 'in_progress_count': in_progress.count(),
        'completed_today_count': completed_today.count(), 'recent_uploads': recent_uploads,
        'todays_revenue': todays_revenue, 'ot_payments': ot_payments,
    })


@operation_theatre_required
def surgery_list(request):
    surgeries = Surgery.objects.select_related('patient', 'surgeon', 'ot_room', 'patient__district')
    status = request.GET.get('status', '')
    department = request.GET.get('department', '')
    q = request.GET.get('q', '').strip()
    if status:
        surgeries = surgeries.filter(status=status)
    if department:
        surgeries = surgeries.filter(surgeon__department_id=department)
    if q:
        surgeries = surgeries.filter(
            Q(surgery_number__icontains=q) |
            Q(patient__patient_code__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(patient__phone_number__icontains=q) |
            Q(surgery_name__icontains=q)
        )
    from departments.models import Department
    return render(request, 'operation_theatre/surgery_list.html', {
        'surgeries': surgeries, 'statuses': Surgery.Status.choices, 'selected_status': status,
        'departments': Department.objects.filter(is_active=True), 'selected_department': department, 'q': q,
    })


@operation_theatre_required
def surgery_schedule(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = SurgeryScheduleForm(request.POST, patient=patient)
        if form.is_valid():
            surgery = form.save(commit=False)
            surgery.patient = patient
            if surgery.operation_type:
                surgery.surgery_name = surgery.surgery_name or surgery.operation_type.name
                surgery.charge_amount = surgery.operation_type.fixed_price
            surgery.created_by = request.user
            surgery.save()

            for f in request.FILES.getlist('consent_files'):
                PatientDocument.objects.create(
                    patient=patient,
                    category=DocumentCategory.CONSENT_FORM,
                    title=f"Consent / Referral - {surgery.surgery_name}",
                    file=f,
                    department_note='Operation Theatre',
                    remarks=surgery.pre_op_notes,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.SURGERY_SCHEDULED,
                f"Scheduled surgery \"{surgery.surgery_name}\" for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=surgery.surgery_number,
            )
            messages.success(request, f'Surgery scheduled. Ref: {surgery.surgery_number}')
            return redirect('operation_theatre:surgery_detail', pk=surgery.pk)
    else:
        form = SurgeryScheduleForm(patient=patient)
    return render(request, 'operation_theatre/surgery_schedule.html', {'form': form, 'patient': patient})


@operation_theatre_required
def surgery_slip(request, pk):
    """Printable Operation Theatre Slip - same unified print identity as every other document."""
    surgery = get_object_or_404(
        Surgery.objects.select_related('patient', 'surgeon', 'ot_room', 'admission'), pk=pk,
    )
    return render(request, 'operation_theatre/surgery_slip.html', {'surgery': surgery})


@operation_theatre_required
def surgery_detail(request, pk):
    surgery = get_object_or_404(
        Surgery.objects.select_related('patient', 'surgeon', 'ot_room', 'admission'), pk=pk,
    )
    uploaded_docs = PatientDocument.objects.filter(
        patient=surgery.patient, department_note='Operation Theatre', is_active=True,
    ).order_by('-uploaded_at')

    if request.method == 'POST':
        form = SurgeryUpdateForm(request.POST, instance=surgery)
        if form.is_valid():
            form.save()

            for f in request.FILES.getlist('operative_files'):
                PatientDocument.objects.create(
                    patient=surgery.patient,
                    category=DocumentCategory.OPERATION_RECORD,
                    title=f"{surgery.surgery_name} - Operative Report - {timezone.now().date()}",
                    file=f,
                    department_note='Operation Theatre',
                    remarks=surgery.operative_notes or surgery.post_op_notes,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.SURGERY_UPDATED,
                f"Surgery record updated: {surgery.surgery_number} ({surgery.get_status_display()})",
                patient_id_text=surgery.patient.patient_code, receipt_number=surgery.surgery_number,
            )
            messages.success(request, 'Surgery record updated.')
            return redirect('operation_theatre:surgery_detail', pk=surgery.pk)
    else:
        form = SurgeryUpdateForm(instance=surgery)
    return render(request, 'operation_theatre/surgery_detail.html', {
        'surgery': surgery, 'form': form, 'uploaded_docs': uploaded_docs,
    })
