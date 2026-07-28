import datetime

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import operation_theatre_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from documents.models import PatientDocument, DocumentCategory
from operation_theatre.forms import SurgeryScheduleForm, SurgeryUpdateForm
from operation_theatre.models import Surgery
from patients.models import Patient


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
    scheduled = Surgery.objects.filter(status=Surgery.Status.SCHEDULED).select_related('patient', 'surgeon')
    today_list = scheduled.filter(scheduled_datetime__date=today)
    in_progress = Surgery.objects.filter(status=Surgery.Status.IN_PROGRESS).select_related('patient', 'surgeon')
    completed_today = Surgery.objects.filter(status=Surgery.Status.COMPLETED, completed_at__date=today)
    recent_uploads = PatientDocument.objects.filter(
        category__in=[DocumentCategory.OPERATION_RECORD, DocumentCategory.CONSENT_FORM],
    ).select_related('patient', 'uploaded_by').order_by('-uploaded_at')[:10]

    return render(request, 'operation_theatre/dashboard.html', {
        'today_list': today_list, 'in_progress': in_progress,
        'scheduled_count': scheduled.count(), 'in_progress_count': in_progress.count(),
        'completed_today_count': completed_today.count(), 'recent_uploads': recent_uploads,
    })


@operation_theatre_required
def surgery_list(request):
    surgeries = Surgery.objects.select_related('patient', 'surgeon', 'ot_room').all()
    status = request.GET.get('status', '')
    if status:
        surgeries = surgeries.filter(status=status)
    return render(request, 'operation_theatre/surgery_list.html', {
        'surgeries': surgeries, 'statuses': Surgery.Status.choices, 'selected_status': status,
    })


@operation_theatre_required
def surgery_schedule(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = SurgeryScheduleForm(request.POST, patient=patient)
        if form.is_valid():
            surgery = form.save(commit=False)
            surgery.patient = patient
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
