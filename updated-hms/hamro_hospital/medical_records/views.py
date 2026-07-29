from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from accounts.decorators import medical_records_required
from consultations.models import Consultation, LabTestRequest, RadiologyRequest, PrescriptionItem
from patients.models import Patient


@medical_records_required
def dashboard(request):
    return render(request, 'medical_records/dashboard.html', {
        'patient_count': Patient.objects.count(),
    })


@medical_records_required
def patient_search(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'medical_records/patient_search.html', {'q': q, 'patients': patients})


@medical_records_required
def patient_full_record(request, patient_id):
    """
    The complete digital file for one patient (spec section 2): OPD history,
    admissions, billing, pharmacy, lab, radiology, prescriptions, doctor
    notes, operation records, discharge summaries, and documents - all in
    one read-only view for the Medical Records department.
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    consultations = Consultation.objects.filter(visit__patient=patient).select_related('visit', 'doctor')
    return render(request, 'medical_records/patient_full_record.html', {
        'patient': patient,
        'consultations': consultations,
        'admissions': patient.admissions.select_related('ward', 'admitting_doctor'),
        'bills': patient.bills.all(),
        'lab_requests': LabTestRequest.objects.filter(
            Q(consultation__visit__patient=patient) | Q(patient=patient)
        ),
        'radiology_requests': RadiologyRequest.objects.filter(
            Q(consultation__visit__patient=patient) | Q(patient=patient)
        ),
        'prescription_items': PrescriptionItem.objects.filter(consultation__visit__patient=patient),
        'surgeries': patient.surgeries.select_related('surgeon'),
        'documents': patient.documents.filter(is_active=True),
    })
