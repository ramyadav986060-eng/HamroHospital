from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import role_required, super_admin_required
from accounts.models import Role, AuditLog
from accounts.utils import write_audit_log
from admissions.models import Admission, Ward, Bed
from admissions.forms import AdmissionForm, DischargeForm, WardForm, BedForm

# Doctors do not admit patients directly; they send Admission Referrals.
admissions_staff_required = role_required(Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.WARD_ADMISSION, Role.NURSING)


@admissions_staff_required
def admission_list(request):
    import datetime
    from consultations.models import Consultation
    from billing.models import Bill
    from django.db.models import Exists, OuterRef, Sum
    
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    admissions = Admission.objects.select_related('patient', 'ward', 'bed', 'department').all()
    status = request.GET.get('status', '')
    if status:
        admissions = admissions.filter(status=status)

    date_str = request.GET.get('date', '')
    selected_date = None
    if date_str:
        try:
            selected_date = datetime.date.fromisoformat(date_str)
            admissions = admissions.filter(admission_date__date=selected_date)
        except ValueError:
            selected_date = None

    # Load dynamic inpatient recommendations from consultations (spec section 12)
    from referrals.models import Referral
    admission_referrals = Referral.objects.filter(
        referral_type=Referral.ReferralType.ADMISSION,
        status__in=['new', 'acknowledged', 'in_progress'],
    ).select_related('patient', 'referred_by', 'to_department')
    active_admissions = Admission.objects.filter(patient=OuterRef('visit__patient'), status=Admission.Status.ADMITTED)
    recommended_admissions = Consultation.objects.filter(
        recommend_admission=True
    ).annotate(
        is_already_admitted=Exists(active_admissions)
    ).filter(
        is_already_admitted=False
    ).select_related('visit__patient', 'visit__department', 'doctor')

    currently_admitted = Admission.objects.filter(status=Admission.Status.ADMITTED).select_related('patient', 'ward', 'bed')
    todays_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date=today).aggregate(t=Sum('total_amount'))['t'] or 0
    monthly_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date__gte=month_start).aggregate(t=Sum('total_amount'))['t'] or 0
    yearly_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date__gte=year_start).aggregate(t=Sum('total_amount'))['t'] or 0
    pending_admissions_count = admission_referrals.count()

    return render(request, 'admissions/admission_list.html', {
        'admissions': admissions, 'statuses': Admission.Status.choices, 'selected_status': status,
        'selected_date': selected_date,
        'todays_count': Admission.objects.filter(admission_date__date=today).count(),
        'monthly_count': Admission.objects.filter(admission_date__date__gte=month_start).count(),
        'yearly_count': Admission.objects.filter(admission_date__date__gte=year_start).count(),
        'currently_admitted_count': currently_admitted.count(),
        'pending_admissions_count': pending_admissions_count,
        'todays_revenue': todays_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'recommended_admissions': recommended_admissions,
        'admission_referrals': admission_referrals,
        'discharge_queue': currently_admitted.order_by('admission_date')[:15],
    })


@admissions_staff_required
def search_patient(request):
    from django.db.models import Q
    from patients.models import Patient
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).distinct()
    return render(request, 'admissions/search_patient.html', {'q': q, 'patients': patients})


@admissions_staff_required
def admit_patient(request, patient_id):
    from patients.models import Patient
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.patient = patient
            admission.created_by = request.user
            admission.save()
            write_audit_log(
                request, AuditLog.Action.ADMISSION,
                f"Admitted {patient.full_name} to {admission.ward.name}",
                patient_id_text=patient.patient_code, receipt_number=admission.admission_number,
            )
            messages.success(request, f'{patient.full_name} admitted. Admission #: {admission.admission_number}')
            return redirect('admissions:admission_detail', pk=admission.pk)
    else:
        initial = {}
        referral_id = request.GET.get('referral')
        if referral_id:
            from referrals.models import Referral
            referral = Referral.objects.filter(pk=referral_id, patient=patient).first()
            if referral:
                initial = {
                    'department': referral.to_department_id,
                    'reason_for_admission': referral.reason,
                    'diagnosis': referral.diagnosis,
                }
        form = AdmissionForm(initial=initial)
    return render(request, 'admissions/admit_form.html', {'form': form, 'patient': patient})


@admissions_staff_required
def admission_detail(request, pk):
    admission = get_object_or_404(
        Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor'), pk=pk,
    )
    discharge_form = DischargeForm() if admission.status == Admission.Status.ADMITTED else None
    return render(request, 'admissions/admission_detail.html', {
        'admission': admission, 'discharge_form': discharge_form,
    })


@admissions_staff_required
def admission_slip(request, pk):
    """Printable Admission Slip - same unified print identity as every other document."""
    admission = get_object_or_404(
        Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor'), pk=pk,
    )
    return render(request, 'admissions/admission_slip.html', {'admission': admission})


@admissions_staff_required
def discharge_patient(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        from billing.models import Bill
        pending_bills = Bill.objects.filter(patient=admission.patient, status=Bill.Status.PENDING)
        if pending_bills.exists():
            messages.error(request, 'Cannot discharge: patient has pending payments. Please clear all bills first.')
            return redirect('admissions:admission_detail', pk=admission.pk)
        form = DischargeForm(request.POST)
        if form.is_valid():
            admission.discharge(
                condition=form.cleaned_data['discharge_condition'],
                summary=form.cleaned_data['discharge_summary'],
                follow_up_instructions=form.cleaned_data['follow_up_instructions'],
            )
            write_audit_log(
                request, AuditLog.Action.DISCHARGE,
                f"Discharged {admission.patient.full_name} ({admission.get_discharge_condition_display()})",
                patient_id_text=admission.patient.patient_code, receipt_number=admission.admission_number,
            )
            messages.success(request, f'{admission.patient.full_name} discharged. Bed freed.')
            return redirect('admissions:admission_detail', pk=admission.pk)
    return redirect('admissions:admission_detail', pk=admission.pk)


# --- Ward / Bed management (Super Admin only) -------------------------------

@admissions_staff_required
def ward_list(request):
    wards = Ward.objects.prefetch_related('beds').all()
    return render(request, 'admissions/ward_list.html', {'wards': wards})


@super_admin_required
def ward_create(request):
    if request.method == 'POST':
        form = WardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ward created.')
            return redirect('admissions:ward_list')
    else:
        form = WardForm()
    return render(request, 'admissions/ward_form.html', {'form': form, 'title': 'Add Ward'})


@super_admin_required
def bed_create(request):
    if request.method == 'POST':
        form = BedForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bed added.')
            return redirect('admissions:ward_list')
    else:
        form = BedForm()
    return render(request, 'admissions/bed_form.html', {'form': form, 'title': 'Add Bed'})
