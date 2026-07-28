import datetime

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import nursing_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from admissions.models import Admission
from documents.models import PatientDocument, DocumentCategory
from nursing.forms import NursingNoteForm
from nursing.models import NursingNote
from patients.models import Patient


@nursing_required
def dashboard(request):
    today = datetime.date.today()

    # "My Assigned Patients" (spec 9): this build has no per-nurse ward
    # assignment model yet, so every currently-admitted patient is shown -
    # see the status doc for the follow-up needed to scope this per nurse.
    active_admissions = Admission.objects.filter(
        status=Admission.Status.ADMITTED,
    ).select_related('patient', 'ward', 'bed')

    todays_admissions = Admission.objects.filter(admission_date__date=today)
    todays_discharges = Admission.objects.filter(discharge_date__date=today)

    # Pending Nursing Notes: admitted patients with no note recorded yet today.
    admissions_with_note_today = NursingNote.objects.filter(
        recorded_at__date=today,
    ).values_list('admission_id', flat=True)
    pending_notes = active_admissions.exclude(pk__in=admissions_with_note_today)

    return render(request, 'nursing/dashboard.html', {
        'active_admissions': active_admissions,
        'active_count': active_admissions.count(),
        'todays_admissions_count': todays_admissions.count(),
        'todays_discharges_count': todays_discharges.count(),
        'pending_notes': pending_notes,
        'pending_notes_count': pending_notes.count(),
    })


@nursing_required
def search_patient(request):
    """Large search box (spec 9): Patient ID, QR Code, Phone Number, Name."""
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).distinct()
    return render(request, 'nursing/search_patient.html', {'q': q, 'patients': patients})


@nursing_required
def admission_notes(request, admission_id):
    admission = get_object_or_404(
        Admission.objects.select_related('patient', 'ward', 'bed'), pk=admission_id,
    )
    notes = admission.nursing_notes.select_related('recorded_by').all()
    uploaded_docs = PatientDocument.objects.filter(
        patient=admission.patient, department_note='Nursing', is_active=True,
    ).order_by('-uploaded_at')

    if request.method == 'POST':
        form = NursingNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.admission = admission
            note.recorded_by = request.user
            note.save()

            # Upload PDF / Upload Scanned Nursing Documents (spec 9) - each
            # file becomes its own PatientDocument, which is what already
            # fans out into the patient's permanent Medical Record.
            for f in request.FILES.getlist('attachment_files'):
                PatientDocument.objects.create(
                    patient=admission.patient,
                    category=DocumentCategory.NURSING_NOTE,
                    title=f"Nursing - {note.get_note_type_display()} - {note.recorded_at.date() if note.recorded_at else datetime.date.today()}",
                    file=f,
                    department_note='Nursing',
                    remarks=note.content,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.NURSING_NOTE,
                f"{note.get_note_type_display()} recorded for {admission.patient.full_name}",
                patient_id_text=admission.patient.patient_code,
            )
            messages.success(request, 'Nursing note recorded.')
            return redirect('nursing:admission_notes', admission_id=admission.pk)
    else:
        form = NursingNoteForm()

    return render(request, 'nursing/admission_notes.html', {
        'admission': admission, 'notes': notes, 'form': form, 'uploaded_docs': uploaded_docs,
    })
