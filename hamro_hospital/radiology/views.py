import datetime

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import radiology_required, role_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log
from consultations.models import RadiologyRequest, RequestStatus, Urgency
from documents.models import PatientDocument, DocumentCategory
from radiology.forms import RadiologyReportForm, ManualRadiologyRequestForm
from patients.models import Patient


@radiology_required
def dashboard(request):
    today = datetime.date.today()
    pending = RadiologyRequest.objects.filter(status=RequestStatus.REQUESTED)
    accepted = RadiologyRequest.objects.filter(status=RequestStatus.ACCEPTED)
    imaging_queue = RadiologyRequest.objects.filter(
        status__in=[RequestStatus.SAMPLE_COLLECTED, RequestStatus.IN_PROGRESS]
    )
    completed_today = RadiologyRequest.objects.filter(status=RequestStatus.COMPLETED, completed_at__date=today)
    urgent = RadiologyRequest.objects.filter(urgency__in=[Urgency.URGENT, Urgency.STAT]).exclude(status=RequestStatus.COMPLETED)

    recent_uploads = PatientDocument.objects.filter(
        category=DocumentCategory.RADIOLOGY_REPORT,
    ).select_related('patient', 'uploaded_by').order_by('-uploaded_at')[:10]

    return render(request, 'radiology/dashboard.html', {
        'pending_count': pending.count(),
        'accepted_count': accepted.count(),
        'imaging_queue_count': imaging_queue.count(),
        'completed_today_count': completed_today.count(),
        'urgent_count': urgent.count(),
        'recent_uploads': recent_uploads,
    })


@radiology_required
def search_patient(request):
    """Large search box (spec 6): Patient ID, QR, Phone, Name."""
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).distinct()
    return render(request, 'radiology/search_patient.html', {'q': q, 'patients': patients})


@radiology_required
def manual_create(request, patient_id):
    """Radiology staff manually opens a record for a walk-in patient who
    arrived with a physical referral letter (spec 6). Skips straight to
    Accepted since staff already has the referral in hand."""
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = ManualRadiologyRequestForm(request.POST, request.FILES)
        if form.is_valid():
            radiology_request = form.save(commit=False)
            radiology_request.patient = patient
            radiology_request.is_manual = True
            radiology_request.status = RequestStatus.ACCEPTED
            radiology_request.accepted_at = timezone.now()
            radiology_request.accepted_by = request.user
            radiology_request.save()
            write_audit_log(
                request, AuditLog.Action.RADIOLOGY_RESULT,
                f"Walk-in radiology record opened: {radiology_request.display_service_name} for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=radiology_request.radiology_number,
            )
            messages.success(request, f"Radiology record opened for {patient.full_name}.")
            return redirect('radiology:queue')
    else:
        form = ManualRadiologyRequestForm()
    return render(request, 'radiology/manual_create.html', {'form': form, 'patient': patient})


@radiology_required
def accept_request(request, pk):
    """Accept Request button (spec 6): acknowledges the doctor's electronic
    request inside the system - does not touch billing or clinical notes."""
    radiology_request = get_object_or_404(RadiologyRequest, pk=pk)
    if radiology_request.status != RequestStatus.REQUESTED:
        messages.warning(request, "This request has already been accepted or actioned.")
    else:
        radiology_request.status = RequestStatus.ACCEPTED
        radiology_request.accepted_at = timezone.now()
        radiology_request.accepted_by = request.user
        radiology_request.save(update_fields=['status', 'accepted_at', 'accepted_by'])
        write_audit_log(
            request, AuditLog.Action.RADIOLOGY_RESULT,
            f"Radiology request accepted: {radiology_request.display_service_name} for {radiology_request.patient_obj.full_name}",
            patient_id_text=radiology_request.patient_obj.patient_code, receipt_number=radiology_request.radiology_number,
        )
        messages.success(request, 'Request accepted.')
    return redirect(request.META.get('HTTP_REFERER') or 'radiology:queue')


@radiology_required
def request_queue(request):
    requests_qs = RadiologyRequest.objects.select_related(
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
            Q(radiology_number__icontains=q)
        )

    return render(request, 'radiology/queue.html', {
        'requests': requests_qs, 'statuses': RequestStatus.choices, 'selected_status': status, 'q': q,
    })


@radiology_required
def update_report(request, pk):
    radiology_request = get_object_or_404(
        RadiologyRequest.objects.select_related('consultation__visit__patient', 'patient'), pk=pk,
    )

    # Check 24 hours edit window and ownership rules
    if radiology_request.status == RequestStatus.COMPLETED:
        if radiology_request.completed_at and (timezone.now() - radiology_request.completed_at) > datetime.timedelta(hours=24):
            if not request.user.is_superuser:
                messages.error(request, "This radiology report is older than 24 hours. Only a Super Admin can edit it.")
                return redirect('radiology:dashboard')
        if radiology_request.processed_by and radiology_request.processed_by != request.user:
            if not request.user.is_superuser:
                messages.error(request, "You can only edit your own radiology reports.")
                return redirect('radiology:dashboard')

    if request.method == 'POST':
        form = RadiologyReportForm(request.POST, request.FILES, instance=radiology_request)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == RequestStatus.COMPLETED and not updated.completed_at:
                updated.completed_at = timezone.now()
            updated.processed_by = request.user
            updated.save()

            # Multiple files (PDF / scanned report / X-ray/CT/MRI/USG image)
            # -> each becomes its own PatientDocument, fanning out to Medical
            # History / Doctor Dashboard / Patient Portal / Super Admin /
            # Nursing (view-only) / OT (view-only) automatically.
            patient = updated.patient_obj
            report_files = request.FILES.getlist('report_files')
            for f in report_files:
                PatientDocument.objects.create(
                    patient=patient,
                    category=DocumentCategory.RADIOLOGY_REPORT,
                    title=f"{updated.display_service_name} - {timezone.now().date()}",
                    file=f,
                    department_note='Radiology',
                    remarks=updated.impression or updated.report_notes,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.RADIOLOGY_RESULT,
                f"Radiology report updated: {updated.radiology_number} for {patient.full_name}",
                patient_id_text=patient.patient_code,
                receipt_number=updated.radiology_number,
            )

            # Trigger Radiology Report Uploaded notification
            if updated.status == RequestStatus.COMPLETED:
                from accounts.utils import create_notification
                create_notification(
                    title="Radiology Report Uploaded",
                    message=f"Radiology report for {updated.display_service_name} has been uploaded for {patient.full_name}.",
                    role=Role.DOCTOR,
                )

            messages.success(request, 'Radiology report updated.')
            return redirect('radiology:queue')
    else:
        form = RadiologyReportForm(instance=radiology_request)
    return render(request, 'radiology/update_report.html', {'form': form, 'radiology_request': radiology_request})


@role_required(Role.SUPER_ADMIN, Role.RADIOLOGY, Role.DOCTOR, Role.WARD_ADMISSION, Role.NURSING, Role.OPERATION_THEATRE)
def print_report(request, pk):
    radiology_request = get_object_or_404(
        RadiologyRequest.objects.select_related('consultation__visit__patient', 'consultation__visit__department', 'patient'), pk=pk,
    )
    return render(request, 'radiology/report_print.html', {'radiology_request': radiology_request})
