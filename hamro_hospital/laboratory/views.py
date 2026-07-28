import datetime

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import laboratory_required, role_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log
from consultations.models import LabTestRequest, RequestStatus, Urgency
from documents.models import PatientDocument, DocumentCategory
from laboratory.forms import LabResultForm, ManualLabRequestForm
from patients.models import Patient


@laboratory_required
def dashboard(request):
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    pending = LabTestRequest.objects.filter(status=RequestStatus.REQUESTED)
    accepted = LabTestRequest.objects.filter(status=RequestStatus.ACCEPTED)
    sample_collected = LabTestRequest.objects.filter(status=RequestStatus.SAMPLE_COLLECTED)
    in_progress = LabTestRequest.objects.filter(status=RequestStatus.IN_PROGRESS)
    completed_today = LabTestRequest.objects.filter(status=RequestStatus.COMPLETED, completed_at__date=today)
    completed_month = LabTestRequest.objects.filter(status=RequestStatus.COMPLETED, completed_at__date__gte=month_start)
    completed_year = LabTestRequest.objects.filter(status=RequestStatus.COMPLETED, completed_at__date__gte=year_start)
    urgent = LabTestRequest.objects.filter(urgency__in=[Urgency.URGENT, Urgency.STAT]).exclude(status=RequestStatus.COMPLETED)

    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.date.fromisoformat(date_str) if date_str else today
    except ValueError:
        selected_date = today
    history = LabTestRequest.objects.filter(
        status=RequestStatus.COMPLETED, completed_at__date=selected_date,
    ).select_related('consultation__visit__patient', 'patient')

    recent_uploads = PatientDocument.objects.filter(
        category=DocumentCategory.LAB_REPORT,
    ).select_related('patient', 'uploaded_by').order_by('-uploaded_at')[:10]

    return render(request, 'laboratory/dashboard.html', {
        'pending_count': pending.count(),
        'accepted_count': accepted.count(),
        'sample_collected_count': sample_collected.count(),
        'in_progress_count': in_progress.count(),
        'completed_today_count': completed_today.count(),
        'completed_month_count': completed_month.count(),
        'completed_year_count': completed_year.count(),
        'urgent_count': urgent.count(),
        'selected_date': selected_date, 'is_today': selected_date == today, 'history': history,
        'recent_uploads': recent_uploads,
    })


@laboratory_required
def search_patient(request):
    """Large search box (spec 5): Patient ID, QR Code, Phone Number, Name,
    Registration Number. Result rows link straight into 'New Lab Record'
    for the walk-in-with-physical-referral workflow."""
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).distinct()
    return render(request, 'laboratory/search_patient.html', {'q': q, 'patients': patients})


@laboratory_required
def manual_create(request, patient_id):
    """Laboratory staff manually opens a record for a walk-in patient who
    arrived with a physical referral letter instead of an electronic
    request (spec 5). Skips straight to Accepted since staff already has
    the referral in hand."""
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = ManualLabRequestForm(request.POST, request.FILES)
        if form.is_valid():
            lab_request = form.save(commit=False)
            lab_request.patient = patient
            lab_request.is_manual = True
            lab_request.status = RequestStatus.ACCEPTED
            lab_request.accepted_at = timezone.now()
            lab_request.accepted_by = request.user
            lab_request.save()
            write_audit_log(
                request, AuditLog.Action.LAB_RESULT,
                f"Walk-in laboratory record opened: {lab_request.test_name} for {patient.full_name}",
                patient_id_text=patient.patient_code,
            )
            messages.success(request, f"Laboratory record opened for {patient.full_name}.")
            return redirect('laboratory:queue')
    else:
        form = ManualLabRequestForm()
    return render(request, 'laboratory/manual_create.html', {'form': form, 'patient': patient})


@laboratory_required
def accept_request(request, pk):
    """Accept Request button (spec 5): acknowledges the doctor's electronic
    request inside the system - does not touch billing or clinical notes."""
    lab_request = get_object_or_404(LabTestRequest, pk=pk)
    if lab_request.status != RequestStatus.REQUESTED:
        messages.warning(request, "This request has already been accepted or actioned.")
    else:
        lab_request.status = RequestStatus.ACCEPTED
        lab_request.accepted_at = timezone.now()
        lab_request.accepted_by = request.user
        lab_request.save(update_fields=['status', 'accepted_at', 'accepted_by'])
        write_audit_log(
            request, AuditLog.Action.LAB_RESULT,
            f"Laboratory request accepted: {lab_request.test_name} for {lab_request.patient_obj.full_name}",
            patient_id_text=lab_request.patient_obj.patient_code,
        )
        messages.success(request, 'Request accepted.')
    return redirect(request.META.get('HTTP_REFERER') or 'laboratory:queue')


@laboratory_required
def request_queue(request):
    requests_qs = LabTestRequest.objects.select_related(
        'consultation__visit__patient', 'consultation__visit__department', 'patient',
    ).exclude(status=RequestStatus.COMPLETED)

    status = request.GET.get('status', '')
    if status:
        requests_qs = requests_qs.filter(status=status)

    q = request.GET.get('q', '')
    if q:
        requests_qs = requests_qs.filter(
            Q(consultation__visit__patient__patient_code__icontains=q) |
            Q(consultation__visit__patient__first_name__icontains=q) |
            Q(consultation__visit__patient__last_name__icontains=q) |
            Q(patient__patient_code__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(test_name__icontains=q)
        )

    return render(request, 'laboratory/queue.html', {
        'requests': requests_qs, 'statuses': RequestStatus.choices, 'selected_status': status, 'q': q,
    })


@laboratory_required
def update_result(request, pk):
    lab_request = get_object_or_404(
        LabTestRequest.objects.select_related('consultation__visit__patient', 'patient'), pk=pk,
    )

    # Check 24 hours edit window and ownership rules
    if lab_request.status == RequestStatus.COMPLETED:
        if lab_request.completed_at and (timezone.now() - lab_request.completed_at) > datetime.timedelta(hours=24):
            if not request.user.is_superuser:
                messages.error(request, "This laboratory report is older than 24 hours. Only a Super Admin can edit it.")
                return redirect('laboratory:dashboard')
        if lab_request.processed_by and lab_request.processed_by != request.user:
            if not request.user.is_superuser:
                messages.error(request, "You can only edit your own laboratory reports.")
                return redirect('laboratory:dashboard')

    if request.method == 'POST':
        form = LabResultForm(request.POST, request.FILES, instance=lab_request)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == RequestStatus.COMPLETED and not updated.completed_at:
                updated.completed_at = timezone.now()
            updated.processed_by = request.user
            updated.save()

            # Multiple files (PDF / scanned report) -> each becomes its own
            # PatientDocument, so it appears in Medical History, Doctor
            # Dashboard, Patient Portal, Super Admin, Nursing (view-only),
            # OT (view-only) automatically (spec 5: Laboratory Report Upload).
            patient = updated.patient_obj
            report_files = request.FILES.getlist('report_files')
            for f in report_files:
                PatientDocument.objects.create(
                    patient=patient,
                    category=DocumentCategory.LAB_REPORT,
                    title=f"{updated.test_name} - {timezone.now().date()}",
                    file=f,
                    department_note='Laboratory',
                    remarks=updated.result_notes,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.LAB_RESULT,
                f"Lab result updated: {updated.test_name} for {patient.full_name}",
                patient_id_text=patient.patient_code,
            )

            # Trigger Lab Report Uploaded notification
            if updated.status == RequestStatus.COMPLETED:
                from accounts.utils import create_notification
                create_notification(
                    title="Lab Report Uploaded",
                    message=f"Lab report for {updated.test_name} has been uploaded for {patient.full_name}.",
                    role=Role.DOCTOR,
                )

            messages.success(request, 'Lab result updated.')
            return redirect('laboratory:queue')
    else:
        form = LabResultForm(instance=lab_request)
    return render(request, 'laboratory/update_result.html', {'form': form, 'lab_request': lab_request})


@role_required(Role.SUPER_ADMIN, Role.LABORATORY, Role.DOCTOR, Role.WARD_ADMISSION, Role.NURSING, Role.OPERATION_THEATRE)
def print_report(request, pk):
    lab_request = get_object_or_404(
        LabTestRequest.objects.select_related('consultation__visit__patient', 'consultation__visit__department', 'patient'), pk=pk,
    )
    return render(request, 'laboratory/report_print.html', {'lab_request': lab_request})
