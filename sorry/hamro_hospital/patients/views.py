import datetime

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import registration_counter_required, patient_record_viewer_required, any_staff_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log, create_notification
from django.urls import reverse
from patients.forms import PatientForm, VisitForm, PatientSearchForm
from patients.models import Patient, Visit


@registration_counter_required
def dashboard(request):
    import datetime
    from appointments.models import Appointment

    today = datetime.date.today()
    
    # 1. Walk-in Registrations (OPD Visits today)
    todays_visits = Visit.objects.filter(visit_date=today).select_related('patient', 'department', 'doctor')
    
    # 2. Today's Bookings (appointments for today, not yet confirmed/linked to a patient)
    todays_bookings = Appointment.objects.filter(
        preferred_date=today, linked_patient__isnull=True
    ).exclude(payment_status=Appointment.PaymentStatus.FAILED).select_related('department', 'doctor')
    
    # 3. Online Bookings (all pending or paid appointments with date >= today, not yet confirmed)
    online_bookings = Appointment.objects.filter(
        preferred_date__gte=today, linked_patient__isnull=True
    ).exclude(payment_status=Appointment.PaymentStatus.FAILED).select_related('department', 'doctor').order_by('preferred_date', 'preferred_time')

    # 4. Payment Pending (both cash-pending walk-ins and cash-pending online bookings)
    pending_visits = Visit.objects.filter(visit_date=today, payment_status=Visit.PaymentStatus.PENDING).select_related('patient', 'department', 'doctor')
    pending_appointments = Appointment.objects.filter(
        preferred_date__gte=today, payment_status=Appointment.PaymentStatus.PENDING, linked_patient__isnull=True
    ).select_related('department', 'doctor')

    # 5. Payment Completed (paid walk-ins and paid online bookings today)
    completed_visits = Visit.objects.filter(visit_date=today, payment_status=Visit.PaymentStatus.PAID).select_related('patient', 'department', 'doctor')
    completed_appointments = Appointment.objects.filter(
        preferred_date=today, payment_status=Appointment.PaymentStatus.PAID
    ).select_related('department', 'doctor')

    # Registration counters share patient data, but operational/financial queues are separated.
    if request.user.effective_role == Role.EXTENSION_COUNTER:
        todays_visits = todays_visits.filter(is_extension_service=True)
        pending_visits = pending_visits.filter(is_extension_service=True)
        completed_visits = completed_visits.filter(is_extension_service=True)
        todays_bookings = todays_bookings.filter(is_extension_service=True)
        online_bookings = online_bookings.filter(is_extension_service=True)
        pending_appointments = pending_appointments.filter(is_extension_service=True)
        completed_appointments = completed_appointments.filter(is_extension_service=True)
    elif request.user.effective_role == Role.REGISTRATION_COUNTER:
        todays_visits = todays_visits.filter(is_extension_service=False)
        pending_visits = pending_visits.filter(is_extension_service=False)
        completed_visits = completed_visits.filter(is_extension_service=False)
        todays_bookings = todays_bookings.filter(is_extension_service=False)
        online_bookings = online_bookings.filter(is_extension_service=False)
        pending_appointments = pending_appointments.filter(is_extension_service=False)
        completed_appointments = completed_appointments.filter(is_extension_service=False)

    context = {
        'todays_visits': todays_visits,
        'todays_count': todays_visits.count(),
        'todays_new_patients': Patient.objects.filter(created_at__date=today).count(),
        'recent_patients': Patient.objects.filter(created_at__gte=timezone.now() - datetime.timedelta(hours=24)).select_related('district').order_by('-created_at')[:10],
        'todays_bookings': todays_bookings,
        'online_bookings': online_bookings,
        'pending_visits': pending_visits,
        'pending_appointments': pending_appointments,
        'completed_visits': completed_visits,
        'completed_appointments': completed_appointments,
    }
    return render(request, 'patients/dashboard.html', context)


@registration_counter_required
def patient_register(request, extension_mode=False):
    """
    Register a new patient or, when an existing Patient ID/QR/barcode was
    scanned, create a returning-patient OPD visit without duplicating the
    patient record. Scanned returning patients are always charged the old
    patient fee (NPR 50 by default).
    """
    extension_mode = extension_mode or request.GET.get('extension') == '1' or request.POST.get('is_extension_service') == '1'
    extension_doctor_id = request.GET.get('doctor') or request.POST.get('extension_doctor_id')
    existing_patient = None
    existing_patient_id = request.POST.get('existing_patient_id') if request.method == 'POST' else None
    if existing_patient_id:
        existing_patient = Patient.objects.filter(pk=existing_patient_id).first()
    elif request.method == 'POST':
        phone = (request.POST.get('phone_number') or '').strip()
        if phone:
            existing_patient = Patient.objects.filter(phone_number=phone).first()

    if request.method == 'POST':
        patient_form = PatientForm(request.POST, request.FILES, instance=existing_patient) if existing_patient else PatientForm(request.POST, request.FILES)
        visit_form = VisitForm(request.POST)

        patient_ok = True if existing_patient else patient_form.is_valid()
        visit_ok = visit_form.is_valid()
        if patient_ok and visit_ok:
            candidate_visit = visit_form.save(commit=False)
            is_super_admin = getattr(request.user, 'role', None) == Role.SUPER_ADMIN
            if candidate_visit.doctor and not is_super_admin:
                visit_date = candidate_visit.visit_date or datetime.date.today()
                quota_error_context = {
                    'patient_form': patient_form, 'visit_form': visit_form,
                    'new_fee': 100, 'old_fee': 50, 'existing_patient': existing_patient,
                }
                if candidate_visit.doctor.is_on_leave(visit_date):
                    messages.error(request, f"Dr. {candidate_visit.doctor.full_name} is on leave/unavailable today. Please choose another doctor.")
                    return render(request, 'patients/patient_register.html', quota_error_context)
                if not candidate_visit.doctor.is_available_for_date(visit_date):
                    messages.error(request, f"Dr. {candidate_visit.doctor.full_name}'s quota for today is already full. Please choose another doctor.")
                    return render(request, 'patients/patient_register.html', quota_error_context)

            if existing_patient:
                patient = existing_patient
                patient_type = Visit.PatientType.OLD
                if extension_mode and candidate_visit.doctor:
                    registration_fee = candidate_visit.doctor.extension_old_fee
                else:
                    registration_fee = settings.OLD_PATIENT_REGISTRATION_FEE
            else:
                patient = patient_form.save(commit=False)
                patient.created_by = request.user
                patient.save()
                patient_type = visit_form.cleaned_data.get('patient_type') or Visit.PatientType.NEW
                if extension_mode and candidate_visit.doctor:
                    registration_fee = candidate_visit.doctor.extension_new_fee if patient_type == Visit.PatientType.NEW else candidate_visit.doctor.extension_old_fee
                else:
                    registration_fee = visit_form.cleaned_data['registration_fee']

            visit = visit_form.save(commit=False)
            visit.patient = patient
            visit.patient_type = Visit.PatientType.EXTENSION if extension_mode else patient_type
            visit.is_extension_service = extension_mode
            visit.registration_fee = registration_fee
            visit.created_by = request.user
            if visit.payment_method == Visit.PaymentMethod.CASH:
                visit.payment_status = Visit.PaymentStatus.PENDING
            else:
                # eSewa is an online/digital payment channel. In this OPD counter
                # workflow we record it as completed once staff accepts the method.
                visit.payment_status = Visit.PaymentStatus.PAID
            visit.save()

            write_audit_log(
                request, AuditLog.Action.PATIENT_REGISTER,
                f"{'Returning' if existing_patient else 'New'} patient OPD visit for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=visit.receipt_number,
                amount=visit.registration_fee,
            )
            if not existing_patient:
                create_notification(
                    title="Patient Registered",
                    message=f"New patient {patient.full_name} ({patient.patient_code}) has been registered.",
                    role=Role.REGISTRATION_COUNTER
                )
            if visit.payment_status == Visit.PaymentStatus.PENDING:
                create_notification(
                    title="Payment Pending",
                    message=f"OPD registration fee pending for {patient.full_name}. Amount: NPR {visit.registration_fee}.",
                    role=Role.CASH_COUNTER
                )
            messages.success(request, f'OPD visit created successfully. Patient ID: {patient.patient_code}')
            return redirect('patients:opd_ticket', visit_id=visit.id)
    else:
        patient_form = PatientForm()
        initial = {'patient_type': Visit.PatientType.NEW, 'payment_method': Visit.PaymentMethod.CASH}
        if extension_doctor_id:
            initial['doctor'] = extension_doctor_id
        visit_form = VisitForm(initial=initial)

    return render(request, 'patients/patient_register.html', {
        'patient_form': patient_form, 'visit_form': visit_form,
        'new_fee': 100, 'old_fee': 50,
        'existing_patient': existing_patient,
        'extension_mode': extension_mode,
        'extension_doctor_id': extension_doctor_id or '',
    })

@any_staff_required
def patient_search(request):
    form = PatientSearchForm(request.GET or None)
    patients = Patient.objects.none()
    if form.is_valid() and form.cleaned_data['q']:
        q = form.cleaned_data['q']
        qs = Patient.objects.filter(
            Q(patient_code__icontains=q) | 
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | 
            Q(phone_number__icontains=q) |
            Q(gender__iexact=q) |
            Q(district__province__name__icontains=q)
        )
        
        # Try to parse as date (created_at__date)
        import datetime
        try:
            date_q = datetime.date.fromisoformat(q)
            qs = qs | Patient.objects.filter(created_at__date=date_q)
        except ValueError:
            pass

        # Try to parse as age
        if q.isdigit():
            age_q = int(q)
            # Find patients whose calculated age roughly matches (current year - birth_year roughly = age)
            current_year = datetime.date.today().year
            birth_year_q = current_year - age_q
            qs = qs | Patient.objects.filter(date_of_birth__year__in=[birth_year_q - 1, birth_year_q, birth_year_q + 1])
            
        patients = qs.select_related('district').distinct()
        
    return render(request, 'patients/patient_search.html', {'form': form, 'patients': patients})


@any_staff_required
def qr_lookup(request):
    """
    JSON lookup for QR/barcode/hardware-scanner values. Accepts both ?code=
    and the older ?q= parameter, matching the value encoded in the patient's
    QR/barcode (patient_code) or their phone number.
    """
    from django.http import JsonResponse

    code = (request.GET.get('code') or request.GET.get('q') or '').strip()
    if not code:
        return JsonResponse({'found': False, 'error': 'No code supplied.'}, status=400)

    patient = Patient.objects.select_related('district').filter(
        Q(patient_code__iexact=code) | Q(phone_number=code)
    ).first()

    if not patient:
        return JsonResponse({'found': False, 'error': 'No patient matches that code.'})

    return JsonResponse({
        'found': True,
        'id': patient.pk,
        'patient_code': patient.patient_code,
        'first_name': patient.first_name,
        'last_name': patient.last_name,
        'full_name': patient.full_name,
        'phone_number': patient.phone_number,
        'age': patient.age,
        'age_display': patient.age_at_registration or f"{patient.age} Years",
        'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else '',
        'gender': patient.gender,
        'gender_display': patient.get_gender_display(),
        'district_id': patient.district_id,
        'municipality': patient.municipality,
        'ward_number': patient.ward_number or '',
        'local_address': patient.local_address,
        'email': patient.email,
        'blood_group': patient.blood_group,
        'has_insurance': patient.has_insurance,
        'insurance_company_id': patient.insurance_company_id or '',
        'insurance_policy_number': patient.insurance_policy_number,
        'insurance_membership_number': patient.insurance_membership_number,
        'insurance_card_number': patient.insurance_card_number,
        'insurance_expiry_date': patient.insurance_expiry_date.isoformat() if patient.insurance_expiry_date else '',
        'insurance_remarks': patient.insurance_remarks,
        'qr_code_url': patient.qr_code.url if patient.qr_code else '',
        'barcode_url': patient.barcode.url if patient.barcode else '',
        'detail_url': reverse('patients:patient_detail', args=[patient.pk]),
    })

@patient_record_viewer_required
def patient_list(request):
    """
    "View Patients" page (spec section 9): the full patient list, paginated,
    with search and filters - distinct from patient_search's quick lookup
    (which only shows results after a search term is typed).
    """
    from django.core.paginator import Paginator
    from patients.models import District

    patients = Patient.objects.select_related('district').all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = patients.filter(
            Q(patient_code__icontains=q) | 
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | 
            Q(phone_number__icontains=q) |
            Q(gender__iexact=q) |
            Q(district__province__name__icontains=q)
        )
        
        # Try to parse as date (created_at__date)
        import datetime
        try:
            date_q = datetime.date.fromisoformat(q)
            qs = qs | patients.filter(created_at__date=date_q)
        except ValueError:
            pass

        # Try to parse as age
        if q.isdigit():
            age_q = int(q)
            current_year = datetime.date.today().year
            birth_year_q = current_year - age_q
            qs = qs | patients.filter(date_of_birth__year__in=[birth_year_q - 1, birth_year_q, birth_year_q + 1])
            
        patients = qs.distinct()

    gender = request.GET.get('gender', '').strip()
    if gender:
        patients = patients.filter(gender=gender)

    blood_group = request.GET.get('blood_group', '').strip()
    if blood_group:
        patients = patients.filter(blood_group=blood_group)

    district_id = request.GET.get('district', '').strip()
    if district_id:
        patients = patients.filter(district_id=district_id)

    has_insurance = request.GET.get('has_insurance', '').strip()
    if has_insurance == 'yes':
        patients = patients.filter(has_insurance=True)
    elif has_insurance == 'no':
        patients = patients.filter(has_insurance=False)

    paginator = Paginator(patients, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'patients/patient_list.html', {
        'page_obj': page_obj,
        'districts': District.objects.select_related('province').order_by('name'),
        'genders': Patient.Gender.choices,
        'blood_groups': Patient.BloodGroup.choices,
        'q': q, 'selected_gender': gender, 'selected_blood_group': blood_group,
        'selected_district': district_id, 'selected_has_insurance': has_insurance,
    })


@patient_record_viewer_required
def patient_section(request, pk, section):
    """
    One of the patient-profile section pages (Billing / Insurance / Admission /
    Laboratory / Radiology / Pharmacy / Medical Reports / Appointments / Visits). Each
    opens as its own page - the hub in patient_detail only links out to these,
    it never shows the records inline.
    """
    from accounts.models import Role
    patient = get_object_or_404(Patient, pk=pk)

    section_map = {
        'billing': ('Billing', 'billing/_patient_bills.html'),
        'insurance': ('Insurance', 'insurance/_patient_claims.html'),
        'admission': ('Admission', 'admissions/_patient_admissions.html'),
        'laboratory': ('Laboratory Reports', 'laboratory/_patient_lab_reports.html'),
        'radiology': ('Radiology Reports', 'radiology/_patient_radiology_reports.html'),
        'blood_bank': ('Blood Bank History', 'blood_bank/_patient_blood_history.html'),
        'pharmacy': ('Pharmacy', 'pharmacy/_patient_sales.html'),
        'medical_reports': ('Medical Reports', 'documents/_patient_documents.html'),
        'appointments': ('Appointments', 'appointments/_patient_appointments.html'),
        'visits': ('OPD Visit History', 'patients/_patient_visits.html'),
        'referrals': ('Previous Referrals', 'referrals/_patient_referrals.html'),
        'documents': ('Medical Records', 'documents/_patient_documents.html'),
        'timeline': ('Patient Timeline', 'workflow/_patient_timeline.html'),
    }
    if section not in section_map:
        messages.error(request, 'Unknown patient section.')
        return redirect('patients:patient_detail', pk=pk)

    section_title, section_template = section_map[section]
    
    # Enforce strict department-level access rules (RBAC check)
    role = request.user.effective_role
    allowed_roles_for_section = {
        'billing': [
            Role.SUPER_ADMIN, Role.CASH_COUNTER, Role.DOCTOR, Role.WARD_ADMISSION, 
            Role.OPERATION_THEATRE, Role.ACCOUNTS_DEPT
        ],
        'insurance': [
            Role.SUPER_ADMIN, Role.INSURANCE, Role.DOCTOR
        ],
        'admission': [
            Role.SUPER_ADMIN, Role.WARD_ADMISSION, Role.NURSING, Role.DOCTOR, 
            Role.OPERATION_THEATRE
        ],
        'laboratory': [
            Role.SUPER_ADMIN, Role.LABORATORY, Role.DOCTOR, Role.WARD_ADMISSION, 
            Role.NURSING, Role.OPERATION_THEATRE
        ],
        'radiology': [
            Role.SUPER_ADMIN, Role.RADIOLOGY, Role.DOCTOR, Role.WARD_ADMISSION, 
            Role.NURSING, Role.OPERATION_THEATRE
        ],
        'blood_bank': [
            Role.SUPER_ADMIN, Role.BLOOD_BANK, Role.DOCTOR, Role.WARD_ADMISSION,
            Role.NURSING, Role.OPERATION_THEATRE
        ],
        'pharmacy': [
            Role.SUPER_ADMIN, Role.PHARMACY, Role.DOCTOR, Role.WARD_ADMISSION, 
            Role.NURSING
        ],
        'medical_reports': [
            Role.SUPER_ADMIN, Role.DOCTOR, Role.WARD_ADMISSION, Role.NURSING, 
            Role.OPERATION_THEATRE, Role.MEDICAL_RECORDS
        ],
        'appointments': [
            Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.DOCTOR
        ],
        'visits': [
            Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.DOCTOR
        ],
        'referrals': [Role.SUPER_ADMIN, Role.DOCTOR, Role.LABORATORY, Role.RADIOLOGY, Role.PHARMACY, Role.NURSING, Role.WARD_ADMISSION, Role.OPERATION_THEATRE, Role.BLOOD_BANK],
        'documents': [Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.DOCTOR, Role.MEDICAL_RECORDS, Role.NURSING, Role.WARD_ADMISSION],
        'timeline': [Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.DOCTOR, Role.MEDICAL_RECORDS, Role.NURSING, Role.WARD_ADMISSION],
    }

    if section in allowed_roles_for_section:
        if role not in allowed_roles_for_section[section] and not request.user.is_superuser:
            messages.error(request, f"Your role ({request.user.get_role_display()}) does not have permission to view the {section_title} section.")
            return redirect('patients:patient_detail', pk=pk)

    context = {'patient': patient, 'section_title': section_title, 'section': section}

    if section == 'billing':
        from billing.models import Bill
        context['records'] = Bill.objects.filter(patient=patient)
    elif section == 'insurance':
        from insurance.models import InsuranceClaim
        context['records'] = InsuranceClaim.objects.filter(patient=patient)
    elif section == 'admission':
        from admissions.models import Admission
        context['records'] = Admission.objects.filter(patient=patient).select_related('ward', 'bed', 'department')
    elif section == 'laboratory':
        from django.db.models import Q as _Q
        from consultations.models import LabTestRequest
        context['records'] = LabTestRequest.objects.filter(
            _Q(consultation__visit__patient=patient) | _Q(patient=patient)
        ).select_related('consultation__visit', 'patient')
    elif section == 'radiology':
        from django.db.models import Q as _Q
        from consultations.models import RadiologyRequest
        context['records'] = RadiologyRequest.objects.filter(
            _Q(consultation__visit__patient=patient) | _Q(patient=patient)
        ).select_related('consultation__visit', 'patient')
    elif section == 'blood_bank':
        from blood_bank.models import BloodRequest, BloodIssue
        context['blood_requests'] = BloodRequest.objects.filter(patient=patient).select_related('requested_by')
        context['blood_issues'] = BloodIssue.objects.filter(patient=patient).select_related('blood_unit', 'issued_by')
    elif section == 'pharmacy':
        from pharmacy.models import PharmacySale
        context['records'] = PharmacySale.objects.filter(patient=patient)
    elif section == 'medical_reports':
        from documents.models import DocumentCategory
        context['records'] = patient.documents.filter(
            is_active=True,
            category__in=[DocumentCategory.LAB_REPORT, DocumentCategory.RADIOLOGY_REPORT, DocumentCategory.DOCTOR_NOTE, DocumentCategory.DISCHARGE_SUMMARY, DocumentCategory.OPERATION_RECORD, DocumentCategory.OTHER],
        ).select_related('uploaded_by')
    elif section == 'appointments':
        from appointments.models import Appointment
        context['records'] = Appointment.objects.filter(linked_patient=patient)
    elif section == 'visits':
        context['records'] = patient.visits.select_related('department', 'doctor').all()
    elif section == 'referrals':
        from referrals.models import Referral
        context['records'] = Referral.objects.filter(patient=patient).select_related('referred_by', 'to_department', 'related_bill')
    elif section == 'documents':
        context['records'] = patient.documents.filter(is_active=True).select_related('uploaded_by')
    elif section == 'timeline':
        context['records'] = patient.timeline_events.select_related('actor').all()[:500]

    return render(request, section_template, context)


@patient_record_viewer_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = patient.visits.select_related('department', 'doctor').all()
    return render(request, 'patients/patient_detail.html', {
        'patient': patient, 'visits': visits,
        'within_edit_window': patient.is_within_free_edit_window(),
    })


@registration_counter_required
def patient_edit(request, pk):
    """
    Edit patient details. Within 24 hours of registration this is a free
    correction. After 24 hours, editing here still updates the demographic
    record (address, phone, etc. do need to stay accurate) but any *new
    OPD visit* for this patient must go through patient_new_visit, which is
    where the re-registration fee is actually charged - matching the spec's
    "after 24 hours -> new visit is chargeable" rule.
    """
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            write_audit_log(
                request, AuditLog.Action.PATIENT_UPDATE,
                f"Updated patient {patient.full_name}",
                patient_id_text=patient.patient_code,
            )
            messages.success(request, 'Patient details updated.')
            return redirect('patients:patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_edit.html', {
        'form': form, 'patient': patient,
        'within_edit_window': patient.is_within_free_edit_window(),
    })


@registration_counter_required
def patient_new_visit(request, pk):
    """
    Create a new OPD visit for an existing patient (a walk-in return visit,
    or a post-24-hour correction visit). Always charges the appropriate
    New/Old registration fee - no manual entry, matching the spec.
    """
    patient = get_object_or_404(Patient, pk=pk)
    is_correction = 'correction' in request.GET

    if request.method == 'POST':
        visit_form = VisitForm(request.POST)
        if visit_form.is_valid():
            candidate_visit = visit_form.save(commit=False)
            is_super_admin = getattr(request.user, 'role', None) == Role.SUPER_ADMIN
            if candidate_visit.doctor and not is_super_admin:
                visit_date = candidate_visit.visit_date or datetime.date.today()
                error_context = {'visit_form': visit_form, 'patient': patient, 'is_correction': is_correction}
                if candidate_visit.doctor.is_on_leave(visit_date):
                    messages.error(request, f"Dr. {candidate_visit.doctor.full_name} is on leave/unavailable today. Please choose another doctor.")
                    return render(request, 'patients/patient_new_visit.html', error_context)
                if not candidate_visit.doctor.is_available_for_date(visit_date):
                    messages.error(request, f"Dr. {candidate_visit.doctor.full_name}'s quota for today is already full. Please choose another doctor.")
                    return render(request, 'patients/patient_new_visit.html', error_context)

            visit = visit_form.save(commit=False)
            visit.patient = patient
            visit.registration_fee = visit_form.cleaned_data['registration_fee']
            visit.created_by = request.user
            if is_correction:
                last_visit = patient.visits.order_by('-created_at').first()
                visit.is_correction_of = last_visit
            if visit.payment_method == Visit.PaymentMethod.CASH:
                visit.payment_status = Visit.PaymentStatus.PENDING
            else:
                visit.payment_status = Visit.PaymentStatus.PAID
            visit.save()

            action = AuditLog.Action.VISIT_CORRECTION if is_correction else AuditLog.Action.PATIENT_REGISTER
            write_audit_log(
                request, action,
                f"New visit for {patient.full_name}" + (' (correction)' if is_correction else ''),
                patient_id_text=patient.patient_code, receipt_number=visit.receipt_number,
                amount=visit.registration_fee,
            )
            # Create notifications
            if visit.payment_status == Visit.PaymentStatus.PENDING:
                create_notification(
                    title="Payment Pending",
                    message=f"Walk-in visit registration fee pending for {patient.full_name}. Amount: NPR {visit.registration_fee}.",
                    role=Role.CASH_COUNTER
                )
            messages.success(request, f'New OPD visit created. Receipt: {visit.receipt_number}')
            return redirect('patients:opd_ticket', visit_id=visit.id)
    else:
        visit_form = VisitForm(initial={'patient_type': Visit.PatientType.OLD, 'payment_method': Visit.PaymentMethod.CASH})

    return render(request, 'patients/patient_new_visit.html', {
        'visit_form': visit_form, 'patient': patient, 'is_correction': is_correction,
    })


@registration_counter_required
def opd_ticket(request, visit_id):
    visit = get_object_or_404(Visit.objects.select_related('patient', 'department', 'doctor'), pk=visit_id)
    return render(request, 'patients/opd_ticket.html', {'visit': visit, 'patient': visit.patient})


@registration_counter_required
def opd_ticket_reprint(request, visit_id):
    visit = get_object_or_404(Visit.objects.select_related('patient', 'department', 'doctor'), pk=visit_id)
    write_audit_log(
        request, AuditLog.Action.REPRINT, f"Reprinted OPD ticket {visit.receipt_number}",
        patient_id_text=visit.patient.patient_code, receipt_number=visit.receipt_number,
    )
    return render(request, 'patients/opd_ticket.html', {'visit': visit, 'patient': visit.patient, 'is_reprint': True})


@patient_record_viewer_required
def patient_card(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    can_print_patient_card = request.user.is_superuser or request.user.effective_role in [Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER]
    return render(request, 'patients/patient_card.html', {'patient': patient, 'can_print_patient_card': can_print_patient_card})


def get_doctors_for_department(request, department_id):
    """
    Small JSON endpoint used by the registration form's department -> doctor
    dropdown. Only returns doctors who are actually bookable today: not on
    leave/holiday/off-duty, and not already at their daily quota. Super
    Admins see every doctor (with a "quota full" note) so they can override.
    """
    import datetime
    from django.http import JsonResponse
    from doctors.models import Doctor

    today = datetime.date.today()
    all_doctors = Doctor.objects.filter(department_id=department_id, is_active=True)
    is_super_admin = request.user.is_authenticated and getattr(request.user, 'role', None) == 'super_admin'

    results = []
    for doc in all_doctors:
        available = doc.is_available_for_date(today)
        if not available and not is_super_admin:
            continue
        remaining = doc.remaining_quota_for_date(today)
        results.append({
            'id': doc.id,
            'full_name': doc.full_name,
            'consultation_fee': doc.consultation_fee,
            'available': available,
            'remaining_quota': remaining,
            'on_leave': doc.is_on_leave(today),
        })
    return JsonResponse({
        'first_name': patient.first_name,
        'last_name': patient.last_name,
        'phone_number': patient.phone_number,
        'gender': patient.gender,'doctors': results})


@registration_counter_required
def confirm_arrival(request, appointment_id):
    """
    Registration staff confirms physical arrival of an online appointment booking (spec section 10 & 11).
    Frictionless transformation of booking into registered patient and OPD visit!
    """
    from appointments.models import Appointment
    from patients.models import Patient, Visit, District
    from django.db import transaction

    appointment = get_object_or_404(Appointment, pk=appointment_id)
    if appointment.linked_patient:
        messages.warning(request, 'This patient arrival has already been confirmed.')
        return redirect('patients:dashboard')

    with transaction.atomic():
        # 1. Reuse an existing Patient by phone number to preserve one Hospital ID.
        patient = Patient.objects.filter(phone_number=appointment.phone_number).first()
        if not patient:
            patient = Patient.objects.create(
                first_name=appointment.first_name,
                last_name=appointment.last_name,
                gender=appointment.gender,
                date_of_birth=appointment.date_of_birth,
                phone_number=appointment.phone_number,
                district=appointment.district,
                municipality=appointment.municipality,
                ward_number=appointment.ward_number,
                local_address=appointment.local_address,
                email=appointment.email,
                created_by=request.user,
            )

        # 2. Create OPD Visit
        visit = Visit.objects.create(
            patient=patient,
            department=appointment.department,
            doctor=appointment.doctor,
            patient_type=Visit.PatientType.EXTENSION if appointment.is_extension_service else (Visit.PatientType.OLD if appointment.patient_type == 'old' else Visit.PatientType.NEW),
            registration_fee=appointment.registration_fee,
            is_extension_service=appointment.is_extension_service,
            chief_complaint=appointment.chief_complaint,
            created_by=request.user,
            payment_method=Visit.PaymentMethod.ESEWA if appointment.payment_method == 'esewa' else Visit.PaymentMethod.CASH,
            payment_status=Visit.PaymentStatus.PAID if appointment.payment_status == 'paid' else Visit.PaymentStatus.PENDING,
        )

        # 3. Link appointment
        appointment.linked_patient = patient
        appointment.save()

        # Write audit logs
        write_audit_log(
            request, AuditLog.Action.PATIENT_REGISTER,
            f"Confirmed arrival & registered patient {patient.full_name} from Appointment {appointment.appointment_number}",
            patient_id_text=patient.patient_code,
            receipt_number=visit.receipt_number,
        )

    messages.success(request, f"Patient {patient.full_name} arrival confirmed! OPD Visit ticket generated.")
    return redirect('patients:opd_ticket', visit_id=visit.id)


@registration_counter_required
def cancel_booking(request, appointment_id):
    """
    Cancel an online appointment booking (spec section 11).
    """
    from appointments.models import Appointment
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    appointment.payment_status = Appointment.PaymentStatus.FAILED
    appointment.save()
    
    write_audit_log(
        request, AuditLog.Action.OTHER,
        f"Cancelled appointment booking {appointment.appointment_number} for {appointment.full_name}",
        receipt_number=appointment.appointment_number,
    )
    
    messages.success(request, f"Appointment booking {appointment.appointment_number} has been cancelled.")
    return redirect('patients:dashboard')
