from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import super_admin_required, insurance_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from insurance.forms import InsuranceCompanyForm, ClaimSubmitForm, ClaimReviewForm
from insurance.models import InsuranceClaim
from patients.models import Patient, InsuranceCompany


# --- Super Admin: Insurance Company directory --------------------------------

@super_admin_required
def company_list(request):
    companies = InsuranceCompany.objects.all()
    return render(request, 'insurance/company_list.html', {'companies': companies})


@super_admin_required
def company_create(request):
    if request.method == 'POST':
        form = InsuranceCompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insurance company added.')
            return redirect('insurance:company_list')
    else:
        form = InsuranceCompanyForm()
    return render(request, 'insurance/company_form.html', {'form': form, 'title': 'Add Insurance Company'})


@super_admin_required
def company_edit(request, pk):
    company = get_object_or_404(InsuranceCompany, pk=pk)
    if request.method == 'POST':
        form = InsuranceCompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insurance company updated.')
            return redirect('insurance:company_list')
    else:
        form = InsuranceCompanyForm(instance=company)
    return render(request, 'insurance/company_form.html', {'form': form, 'title': f'Edit {company.name}'})


# --- Insurance Counter: claims workflow ---------------------------------------

@insurance_required
def dashboard(request):
    import datetime
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    pending = InsuranceClaim.objects.filter(status=InsuranceClaim.Status.PENDING)

    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.date.fromisoformat(date_str) if date_str else today
    except ValueError:
        selected_date = today
    history = InsuranceClaim.objects.filter(submitted_at__date=selected_date).select_related('patient')

    return render(request, 'insurance/dashboard.html', {
        'pending_count': pending.count(),
        'approved_count': InsuranceClaim.objects.filter(status=InsuranceClaim.Status.APPROVED).count(),
        'settled_count': InsuranceClaim.objects.filter(status=InsuranceClaim.Status.SETTLED).count(),
        'rejected_count': InsuranceClaim.objects.filter(status=InsuranceClaim.Status.REJECTED).count(),
        'todays_count': InsuranceClaim.objects.filter(submitted_at__date=today).count(),
        'monthly_count': InsuranceClaim.objects.filter(submitted_at__date__gte=month_start).count(),
        'yearly_count': InsuranceClaim.objects.filter(submitted_at__date__gte=year_start).count(),
        'selected_date': selected_date, 'is_today': selected_date == today, 'history': history,
    })


@insurance_required
def patient_lookup(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'insurance/patient_lookup.html', {'q': q, 'patients': patients})


@insurance_required
def patient_claims(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    claims = patient.insurance_claims.select_related('insurance_company').all()
    return render(request, 'insurance/patient_claims.html', {'patient': patient, 'claims': claims})


@insurance_required
def claim_submit(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = ClaimSubmitForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.patient = patient
            claim.submitted_by = request.user
            claim.save()
            write_audit_log(
                request, AuditLog.Action.CLAIM_SUBMITTED,
                f"Insurance claim submitted for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=claim.claim_number,
                amount=claim.amount_claimed,
            )
            messages.success(request, f'Claim {claim.claim_number} submitted.')
            return redirect('insurance:patient_claims', patient_id=patient.pk)
    else:
        form = ClaimSubmitForm()
    return render(request, 'insurance/claim_submit.html', {'form': form, 'patient': patient})


@insurance_required
def claim_slip(request, pk):
    """Printable Insurance Claim Slip - same unified print identity as every other document."""
    claim = get_object_or_404(InsuranceClaim.objects.select_related('patient', 'insurance_company'), pk=pk)
    return render(request, 'insurance/claim_slip.html', {'claim': claim})


@insurance_required
def claim_review(request, pk):
    claim = get_object_or_404(InsuranceClaim.objects.select_related('patient', 'insurance_company'), pk=pk)
    if request.method == 'POST':
        form = ClaimReviewForm(request.POST, instance=claim)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.reviewed_by = request.user
            updated.reviewed_at = timezone.now()
            updated.save()
            write_audit_log(
                request, AuditLog.Action.CLAIM_REVIEWED,
                f"Claim {claim.claim_number} reviewed: {updated.get_status_display()}",
                patient_id_text=claim.patient.patient_code, receipt_number=claim.claim_number,
            )
            messages.success(request, f'Claim {claim.claim_number} updated to {updated.get_status_display()}.')
            return redirect('insurance:patient_claims', patient_id=claim.patient.pk)
    else:
        form = ClaimReviewForm(instance=claim)
    return render(request, 'insurance/claim_review.html', {'form': form, 'claim': claim})


@insurance_required
def claims_report(request):
    claims = InsuranceClaim.objects.select_related('patient', 'insurance_company').all()
    status = request.GET.get('status', '')
    if status:
        claims = claims.filter(status=status)
    return render(request, 'insurance/claims_report.html', {
        'claims': claims, 'statuses': InsuranceClaim.Status.choices, 'selected_status': status,
    })
