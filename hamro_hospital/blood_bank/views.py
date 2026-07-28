from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import blood_bank_required, doctor_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from blood_bank.forms import BloodUnitForm, BloodIssueForm, BloodRequestForm
from blood_bank.models import BloodUnit, BloodIssue, BloodRequest, BloodGroup, BloodRequestStatus
from documents.models import PatientDocument, DocumentCategory
from patients.models import Patient


@blood_bank_required
def dashboard(request):
    available = BloodUnit.objects.filter(status=BloodUnit.Status.AVAILABLE)
    near_expiry = available.filter(expiry_date__lte=timezone.now().date() + timezone.timedelta(days=7))
    stock_by_group = {
        group: available.filter(blood_group=group).count() for group, _ in BloodGroup.choices
    }
    pending_requests = BloodRequest.objects.filter(
        status=BloodRequestStatus.PENDING,
    ).select_related('patient', 'requested_by')
    return render(request, 'blood_bank/dashboard.html', {
        'available_count': available.count(),
        'near_expiry_count': near_expiry.count(),
        'issued_today_count': BloodIssue.objects.filter(issued_at__date=timezone.now().date()).count(),
        'stock_by_group': stock_by_group,
        'pending_requests': pending_requests,
        'pending_requests_count': pending_requests.count(),
    })


@blood_bank_required
def request_queue(request):
    requests_qs = BloodRequest.objects.select_related('patient', 'requested_by').all()
    status = request.GET.get('status', '')
    if status:
        requests_qs = requests_qs.filter(status=status)
    return render(request, 'blood_bank/request_queue.html', {
        'requests': requests_qs, 'statuses': BloodRequestStatus.choices, 'selected_status': status,
    })


@blood_bank_required
def inventory_list(request):
    units = BloodUnit.objects.all()
    status = request.GET.get('status', '')
    if status:
        units = units.filter(status=status)
    group = request.GET.get('group', '')
    if group:
        units = units.filter(blood_group=group)
    return render(request, 'blood_bank/inventory_list.html', {
        'units': units, 'statuses': BloodUnit.Status.choices, 'groups': BloodGroup.choices,
        'selected_status': status, 'selected_group': group,
    })


@blood_bank_required
def unit_add(request):
    if request.method == 'POST':
        form = BloodUnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.added_by = request.user
            unit.save()
            write_audit_log(
                request, AuditLog.Action.BLOOD_UNIT_ADDED,
                f"Blood unit added: {unit.bag_number} ({unit.blood_group})",
                receipt_number=unit.bag_number,
            )
            messages.success(request, f'Blood unit {unit.bag_number} added to inventory.')
            return redirect('blood_bank:inventory_list')
    else:
        form = BloodUnitForm()
    return render(request, 'blood_bank/unit_form.html', {'form': form})


@blood_bank_required
def patient_lookup(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'blood_bank/patient_lookup.html', {'q': q, 'patients': patients})


@blood_bank_required
def issue_blood(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    compatible_units = BloodUnit.objects.filter(
        blood_group=patient.blood_group, status=BloodUnit.Status.AVAILABLE,
    ) if patient.blood_group else BloodUnit.objects.none()

    blood_request_id = request.GET.get('request_id') or request.POST.get('request_id')
    blood_request = None
    if blood_request_id:
        blood_request = get_object_or_404(BloodRequest, pk=blood_request_id, patient=patient)

    if request.method == 'POST':
        unit = get_object_or_404(BloodUnit, pk=request.POST.get('blood_unit_id'), status=BloodUnit.Status.AVAILABLE)
        form = BloodIssueForm(request.POST, patient=patient)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.blood_unit = unit
            issue.patient = patient
            issue.blood_request = blood_request
            issue.issued_by = request.user
            issue.issue_report = request.FILES.get('issue_report')
            issue.save()
            BloodUnit.objects.filter(pk=unit.pk).update(status=BloodUnit.Status.ISSUED)
            if blood_request:
                blood_request.status = BloodRequestStatus.ISSUED
                blood_request.save(update_fields=['status'])

            # Upload Issue Report (spec 12) -> patient's permanent Medical Record.
            if issue.issue_report:
                PatientDocument.objects.create(
                    patient=patient,
                    category=DocumentCategory.BLOOD_ISSUE_REPORT,
                    title=f"Blood Issue Report - {unit.bag_number}",
                    file=issue.issue_report,
                    department_note='Blood Bank',
                    remarks=issue.cross_match_notes,
                    uploaded_by=request.user,
                    uploaded_by_role=getattr(request.user, 'role', ''),
                )

            write_audit_log(
                request, AuditLog.Action.BLOOD_ISSUED,
                f"Blood unit {unit.bag_number} issued to {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=unit.bag_number,
            )
            messages.success(request, f'Unit {unit.bag_number} issued to {patient.full_name}.')
            return redirect('blood_bank:inventory_list')
    else:
        form = BloodIssueForm(patient=patient)

    return render(request, 'blood_bank/issue_form.html', {
        'form': form, 'patient': patient, 'compatible_units': compatible_units, 'blood_request': blood_request,
    })


@doctor_required
def doctor_patient_lookup(request):
    """Doctor's entry point to request blood for a patient (spec 12/17:
    'Request Blood Bank' is one of the doctor's request actions)."""
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'blood_bank/doctor_patient_lookup.html', {'q': q, 'patients': patients})


@doctor_required
def doctor_request_create(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = BloodRequestForm(request.POST, initial={'blood_group_needed': patient.blood_group})
        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.patient = patient
            blood_request.requested_by = request.user
            blood_request.save()
            write_audit_log(
                request, AuditLog.Action.BLOOD_REQUESTED,
                f"Blood requested: {blood_request.blood_group_needed} x{blood_request.units_needed} for {patient.full_name}",
                patient_id_text=patient.patient_code,
            )
            messages.success(request, 'Blood Bank request sent.')
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = BloodRequestForm(initial={'blood_group_needed': patient.blood_group} if patient.blood_group else None)
    return render(request, 'blood_bank/doctor_request_create.html', {'form': form, 'patient': patient})
