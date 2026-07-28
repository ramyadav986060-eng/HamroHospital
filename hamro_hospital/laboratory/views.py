import datetime

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import laboratory_required, role_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log
from consultations.models import LabTestRequest, RequestStatus, Urgency
from documents.models import PatientDocument, DocumentCategory
from laboratory.forms import LabResultForm, ManualLabRequestForm, LabResultValueForm
from patients.models import Patient
from laboratory.models import LabPanel, LabParameter, LabResultValue
from referrals.models import Referral
from workflow.models import PatientTimeline
from workflow.utils import add_timeline


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

    incoming_referrals = Referral.objects.filter(referral_type=Referral.ReferralType.LABORATORY, status__in=['new','acknowledged','in_progress']).select_related('patient','referred_by','related_bill')[:10]

    from workflow.models import ServiceOrder
    service_orders = ServiceOrder.objects.filter(service_type=ServiceOrder.ServiceType.LABORATORY).exclude(status=ServiceOrder.Status.COMPLETED).select_related('patient', 'bill')[:10]

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
        'incoming_referrals': incoming_referrals,
        'service_orders': service_orders,
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

            # Structured parameter values (LabPanel/LabParameter/LabResultValue).
            for key, value in request.POST.items():
                if key.startswith('param_value_'):
                    param_id = key.replace('param_value_', '')
                    if not value.strip():
                        continue
                    parameter = LabParameter.objects.filter(pk=param_id).first()
                    if parameter:
                        LabResultValue.objects.update_or_create(
                            lab_request=updated, parameter=parameter,
                            defaults={
                                'value': value.strip(),
                                'flag': request.POST.get(f'param_flag_{param_id}', '').strip(),
                                'remarks': request.POST.get(f'param_remarks_{param_id}', '').strip(),
                            }
                        )

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

            # Trigger Lab Report Uploaded notification back to the requesting doctor.
            if updated.status == RequestStatus.COMPLETED:
                from accounts.utils import create_notification
                target_user = None
                if updated.consultation_id and updated.consultation.doctor and updated.consultation.doctor.user_account_id:
                    target_user = updated.consultation.doctor.user_account
                create_notification(
                    title="Lab Report Uploaded",
                    message=f"Lab report for {updated.test_name} has been uploaded for {patient.full_name}.",
                    user=target_user,
                    role=None if target_user else Role.DOCTOR,
                    related_url=reverse('laboratory:print_report', args=[updated.pk]),
                )
                add_timeline(patient, PatientTimeline.EventType.LAB, f"Lab result completed: {updated.test_name}", updated.result_notes, actor=request.user, related_url=reverse('laboratory:print_report', args=[updated.pk]), source=updated)

            messages.success(request, 'Lab result updated.')
            return redirect('laboratory:queue')
    else:
        form = LabResultForm(instance=lab_request)
    panel = LabPanel.objects.filter(name__iexact=lab_request.test_name, is_active=True).first() or LabPanel.objects.filter(name__icontains=lab_request.test_name, is_active=True).first()
    parameters = panel.parameters.all() if panel else []
    existing_values = {v.parameter_id: v for v in lab_request.parameter_values.all()}
    return render(request, 'laboratory/update_result.html', {
        'form': form, 'lab_request': lab_request, 'panel': panel,
        'parameters': parameters, 'existing_values': existing_values,
    })


@role_required(Role.SUPER_ADMIN, Role.LABORATORY, Role.DOCTOR, Role.WARD_ADMISSION, Role.NURSING, Role.OPERATION_THEATRE)
def print_report(request, pk):
    lab_request = get_object_or_404(
        LabTestRequest.objects.select_related('consultation__visit__patient', 'consultation__visit__department', 'patient'), pk=pk,
    )
    return render(request, 'laboratory/report_print.html', {'lab_request': lab_request})

@laboratory_required
def verify_result(request, pk):
    lab_request = get_object_or_404(LabTestRequest.objects.select_related('consultation__doctor__user_account', 'patient'), pk=pk)
    if lab_request.status != RequestStatus.COMPLETED:
        messages.error(request, 'Only completed lab results can be verified.')
        return redirect('laboratory:update_result', pk=pk)
    if request.method == 'POST':
        lab_request.verified_by = request.user
        lab_request.verified_at = timezone.now()
        lab_request.save(update_fields=['verified_by', 'verified_at'])
        from accounts.utils import create_notification
        doctor_user = lab_request.consultation.doctor.user_account if lab_request.consultation_id and lab_request.consultation.doctor and lab_request.consultation.doctor.user_account_id else None
        create_notification(
            title='Verified Lab Result Ready',
            message=f'Lab result {lab_request.test_name} is verified for {lab_request.patient_obj.full_name}.',
            user=doctor_user,
            role=None if doctor_user else Role.DOCTOR,
            related_url=reverse('laboratory:print_report', args=[lab_request.pk]),
        )
        messages.success(request, 'Lab result verified.')
    return redirect('laboratory:print_report', pk=pk)
