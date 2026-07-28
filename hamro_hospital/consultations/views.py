import datetime

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import doctor_required
from patients.models import Visit
from consultations.models import Consultation, LabTestRequest, RadiologyRequest
from consultations.forms import ConsultationForm, PrescriptionItemFormSet, LabTestRequestForm, RadiologyRequestForm


def _get_doctor_or_none(request):
    return getattr(request.user, 'doctor_profile', None)


@doctor_required
def consultation_queue(request):
    doctor = _get_doctor_or_none(request)
    if not doctor:
        messages.warning(request, 'Your account is not linked to a Doctor profile yet. Ask Super Admin to link it.')
        return render(request, 'consultations/queue.html', {'visits': []})

    today = datetime.date.today()
    visits = (
        Visit.objects.filter(doctor=doctor, visit_date=today)
        .select_related('patient', 'department')
        .order_by('token_number')
    )
    # Annotate whether each visit already has a consultation started
    visit_list = []
    for visit in visits:
        has_consultation = Consultation.objects.filter(visit=visit).exists()
        visit_list.append({'visit': visit, 'has_consultation': has_consultation})

    return render(request, 'consultations/queue.html', {'visits': visit_list, 'doctor': doctor})


@doctor_required
def consultation_detail(request, visit_id):
    """
    Create/edit the consultation for a visit, including the dynamic
    prescription formset and separate quick-add forms for lab & radiology
    requests - all on one screen, matching the spec.
    """
    visit = get_object_or_404(Visit.objects.select_related('patient', 'department'), pk=visit_id)
    consultation, _created = Consultation.objects.get_or_create(
        visit=visit, defaults={'doctor': getattr(request.user, 'doctor_profile', None)},
    )

    if request.method == 'POST':
        form = ConsultationForm(request.POST, request.FILES, instance=consultation)
        formset = PrescriptionItemFormSet(request.POST, instance=consultation)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Consultation saved.')
            return redirect('consultations:consultation_detail', visit_id=visit.id)
    else:
        form = ConsultationForm(instance=consultation)
        formset = PrescriptionItemFormSet(instance=consultation)

    lab_form = LabTestRequestForm()
    radiology_form = RadiologyRequestForm()

    return render(request, 'consultations/consultation_detail.html', {
        'visit': visit, 'patient': visit.patient, 'consultation': consultation,
        'form': form, 'formset': formset,
        'lab_form': lab_form, 'radiology_form': radiology_form,
        'lab_requests': consultation.lab_requests.all(),
        'radiology_requests': consultation.radiology_requests.all(),
    })


@doctor_required
def add_lab_request(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id)
    if request.method == 'POST':
        form = LabTestRequestForm(request.POST)
        if form.is_valid():
            lab_request = form.save(commit=False)
            lab_request.consultation = consultation
            lab_request.save()
            messages.success(request, f'Lab test "{lab_request.test_name}" requested.')
    return redirect('consultations:consultation_detail', visit_id=consultation.visit_id)


@doctor_required
def add_radiology_request(request, consultation_id):
    consultation = get_object_or_404(Consultation, pk=consultation_id)
    if request.method == 'POST':
        form = RadiologyRequestForm(request.POST)
        if form.is_valid():
            radiology_request = form.save(commit=False)
            radiology_request.consultation = consultation
            radiology_request.save()
            messages.success(request, f'{radiology_request.display_service_name} requested. Number: {radiology_request.radiology_number}')
    return redirect('consultations:consultation_detail', visit_id=consultation.visit_id)


@doctor_required
def patient_history(request, patient_id):
    """Full consultation history for a patient, for continuity of care."""
    from patients.models import Patient
    patient = get_object_or_404(Patient, pk=patient_id)
    consultations = (
        Consultation.objects.filter(visit__patient=patient)
        .select_related('visit', 'visit__department', 'doctor')
        .prefetch_related('prescription_items', 'lab_requests', 'radiology_requests')
    )
    return render(request, 'consultations/patient_history.html', {
        'patient': patient, 'consultations': consultations,
    })
