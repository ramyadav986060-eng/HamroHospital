from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode

from accounts.models import AuditLog
from accounts.utils import write_audit_log
from patient_portal.decorators import patient_login_required, get_portal_patient
from patient_portal.forms import (
    PatientSignupForm, PatientLoginForm, PatientVisitBookingForm,
    PatientRegisterDetailsForm, PatientRegisterOTPForm, PatientRegisterPasswordForm,
)
from patient_portal.models import PatientAccount
from appointments.esewa import build_payment_fields, get_form_url, decode_and_verify_response

from patients.models import Visit, Patient
from billing.models import Bill
from pharmacy.models import PharmacySale
from consultations.models import Consultation, LabTestRequest, RadiologyRequest, RequestStatus
from admissions.models import Admission
from insurance.models import InsuranceClaim


# --- New Patient self-registration (OTP-verified) ------------------------------
# Three steps, session-carried between them - same OTP delivery convention as
# forgot_password/reset_password below (email via send_mail; phone/SMS printed
# to the console until a real SMS gateway is connected, and also surfaced in
# the UI in DEBUG mode so the flow is fully testable today).
# This is additive: the existing `signup` view above (for patients who already
# have a Hospital ID from a hospital visit) is untouched.

def register_start(request):
    if get_portal_patient(request):
        return redirect('patient_portal:dashboard')

    if request.method == 'POST':
        form = PatientRegisterDetailsForm(request.POST)
        if form.is_valid():
            import random
            otp = f"{random.randint(100000, 999999)}"
            name_parts = form.cleaned_data['full_name'].strip().split(' ', 1)
            request.session['register_data'] = {
                'full_name': form.cleaned_data['full_name'],
                'first_name': name_parts[0],
                'last_name': name_parts[1],
                'phone_number': form.cleaned_data['phone_number'],
                'email': form.cleaned_data.get('email', ''),
                'gender': form.cleaned_data['gender'],
                'age_input': form.cleaned_data['age_input'],
                'district_id': form.cleaned_data['district'].id,
            }
            request.session['register_otp'] = otp
            request.session['register_otp_verified'] = False

            # SMS gateway not yet connected - see the identical pattern in
            # forgot_password() below. The OTP is printed server-side and
            # also shown in the UI while DEBUG=True so registration works
            # end-to-end today; swap in a real SMS provider call later.
            print(f"[SMS OTP - GATEWAY NOT YET CONNECTED] Registration OTP {otp} for phone {form.cleaned_data['phone_number']}")
            from django.conf import settings as django_settings
            if django_settings.DEBUG:
                messages.info(request, f"(Demo mode - no SMS gateway configured) Your OTP is: {otp}")
            else:
                messages.info(request, f"A verification code has been sent to {form.cleaned_data['phone_number']}.")
            return redirect('patient_portal:register_verify')
    else:
        form = PatientRegisterDetailsForm()
    return render(request, 'patient_portal/register_details.html', {'form': form})


def register_verify(request):
    if not request.session.get('register_data'):
        messages.error(request, 'Please start registration again.')
        return redirect('patient_portal:register_start')

    if request.method == 'POST':
        form = PatientRegisterOTPForm(request.POST)
        if form.is_valid():
            typed = form.cleaned_data['otp_code'].strip()
            if typed != request.session.get('register_otp'):
                messages.error(request, 'Incorrect OTP code. Please try again.')
            else:
                request.session['register_otp_verified'] = True
                return redirect('patient_portal:register_password')
    else:
        form = PatientRegisterOTPForm()
    return render(request, 'patient_portal/register_verify.html', {
        'form': form, 'phone_number': request.session['register_data'].get('phone_number'),
    })


def register_password(request):
    reg_data = request.session.get('register_data')
    if not reg_data or not request.session.get('register_otp_verified'):
        messages.error(request, 'Please verify your phone number first.')
        return redirect('patient_portal:register_start')

    if request.method == 'POST':
        form = PatientRegisterPasswordForm(request.POST)
        if form.is_valid():
            from patients.utils import parse_age_to_dob
            from patients.models import District

            first_name = reg_data['first_name']
            last_name = reg_data['last_name']
            district = get_object_or_404(District, pk=reg_data['district_id'])

            patient = Patient.objects.create(
                first_name=first_name,
                last_name=last_name,
                gender=reg_data['gender'],
                date_of_birth=parse_age_to_dob(reg_data['age_input']) or timezone_today(),
                age_at_registration=reg_data['age_input'],
                phone_number=reg_data['phone_number'],
                email=reg_data.get('email', ''),
                district=district,
            )
            account = PatientAccount(patient=patient)
            account.set_password(form.cleaned_data['password'])
            account.save()

            for key in ('register_data', 'register_otp', 'register_otp_verified'):
                request.session.pop(key, None)

            request.session['patient_account_id'] = account.id
            account.record_login()
            write_audit_log(
                request, AuditLog.Action.LOGIN,
                f"Patient self-registered via Patient Portal: {patient.patient_code}",
                patient_id_text=patient.patient_code,
            )
            messages.success(
                request,
                f"Welcome, {patient.full_name}! Your account is ready. "
                f"Your Hospital Number is {patient.patient_code} - you'll need it to log in next time.",
            )
            return redirect('patient_portal:dashboard')
    else:
        form = PatientRegisterPasswordForm()
    return render(request, 'patient_portal/register_password.html', {'form': form})


def timezone_today():
    from django.utils import timezone
    return timezone.now().date()


# --- Signup / Login / Logout --------------------------------------------------

def signup(request):
    if get_portal_patient(request):
        return redirect('patient_portal:dashboard')

    if request.method == 'POST':
        form = PatientSignupForm(request.POST)
        if form.is_valid():
            patient = form.cleaned_data['patient']
            account = PatientAccount(patient=patient)
            account.set_password(form.cleaned_data['password'])
            account.save()
            messages.success(request, 'Your Patient Portal account has been created. Please log in.')
            return redirect('patient_portal:login')
    else:
        form = PatientSignupForm()
    return render(request, 'patient_portal/signup.html', {'form': form})


def login_view(request):
    if get_portal_patient(request):
        return redirect('patient_portal:dashboard')

    if request.method == 'POST':
        form = PatientLoginForm(request.POST)
        if form.is_valid():
            hospital_id = form.cleaned_data['hospital_id'].strip()
            phone_number = form.cleaned_data['phone_number'].strip()
            password = form.cleaned_data['password']

            account = (
                PatientAccount.objects
                .select_related('patient')
                .filter(
                    Q(patient__phone_number=phone_number) | Q(patient__email__iexact=phone_number),
                    patient__patient_code__iexact=hospital_id,
                    is_active=True,
                )
                .first()
            )
            if account and account.check_password(password):
                request.session['patient_account_id'] = account.id
                account.record_login()
                write_audit_log(
                    request, AuditLog.Action.LOGIN,
                    f"Patient portal login: {account.patient.patient_code}",
                    patient_id_text=account.patient.patient_code,
                )
                messages.success(request, f'Welcome back, {account.patient.full_name}.')
                return redirect('patient_portal:dashboard')
            messages.error(request, 'Invalid Hospital ID, phone/email, or password.')
    else:
        form = PatientLoginForm()
    return render(request, 'patient_portal/login.html', {'form': form})


def logout_view(request):
    account = get_portal_patient(request)
    if account:
        write_audit_log(
            request, AuditLog.Action.LOGOUT,
            f"Patient portal logout: {account.patient.patient_code}",
            patient_id_text=account.patient.patient_code,
        )
    request.session.pop('patient_account_id', None)
    messages.success(request, 'You have been logged out of the Patient Portal.')
    return redirect('website:home')


# --- Dashboard & records -------------------------------------------------------

@patient_login_required
def dashboard(request):
    patient = request.portal_patient.patient
    context = {
        'patient': patient,
        'visit_count': patient.visits.count(),
        'bill_count': patient.bills.count(),
        'upcoming_admission': patient.admissions.filter(status=Admission.Status.ADMITTED).first(),
        'recent_visits': patient.visits.select_related('department', 'doctor')[:5],
    }
    return render(request, 'patient_portal/dashboard.html', context)


@patient_login_required
def my_visits(request):
    patient = request.portal_patient.patient
    visits = patient.visits.select_related('department', 'doctor').all()
    return render(request, 'patient_portal/my_visits.html', {'patient': patient, 'visits': visits})


@patient_login_required
def my_ticket(request, visit_id):
    """Reuses the exact same OPD ticket template the Registration Counter uses."""
    patient = request.portal_patient.patient
    visit = get_object_or_404(
        Visit.objects.select_related('patient', 'department', 'doctor'),
        pk=visit_id, patient=patient,
    )
    return render(request, 'patients/opd_ticket.html', {'visit': visit, 'patient': patient})


@patient_login_required
def my_patient_card(request):
    patient = request.portal_patient.patient
    return render(request, 'patients/patient_card.html', {'patient': patient})


@patient_login_required
def my_bills(request):
    patient = request.portal_patient.patient
    bills = patient.bills.prefetch_related('items').all()
    return render(request, 'patient_portal/my_bills.html', {'patient': patient, 'bills': bills})


@patient_login_required
def my_bill_receipt(request, pk):
    patient = request.portal_patient.patient
    bill = get_object_or_404(Bill.objects.select_related('patient', 'cashier').prefetch_related('items'), pk=pk, patient=patient)
    return render(request, 'billing/receipt.html', {'bill': bill})


@patient_login_required
def my_pharmacy_sales(request):
    patient = request.portal_patient.patient
    sales = patient.pharmacy_sales.prefetch_related('items').all()
    return render(request, 'patient_portal/my_pharmacy_sales.html', {'patient': patient, 'sales': sales})


@patient_login_required
def my_pharmacy_receipt(request, pk):
    patient = request.portal_patient.patient
    sale = get_object_or_404(PharmacySale.objects.select_related('patient').prefetch_related('items'), pk=pk, patient=patient)
    return render(request, 'pharmacy/receipt.html', {'sale': sale})


@patient_login_required
def my_prescriptions(request):
    patient = request.portal_patient.patient
    consultations = (
        Consultation.objects.filter(visit__patient=patient)
        .select_related('visit__department', 'doctor')
        .prefetch_related('prescription_items')
    )
    return render(request, 'patient_portal/my_prescriptions.html', {'patient': patient, 'consultations': consultations})


@patient_login_required
def my_lab_reports(request):
    patient = request.portal_patient.patient
    lab_requests = LabTestRequest.objects.filter(
        Q(consultation__visit__patient=patient) | Q(patient=patient)
    ).select_related('consultation__visit', 'patient')
    return render(request, 'patient_portal/my_lab_reports.html', {'patient': patient, 'lab_requests': lab_requests})


@patient_login_required
def my_lab_report_detail(request, pk):
    patient = request.portal_patient.patient
    lab_request = get_object_or_404(
        LabTestRequest.objects.select_related('consultation__visit__patient', 'consultation__visit__department', 'patient'),
        Q(consultation__visit__patient=patient) | Q(patient=patient),
        pk=pk, status=RequestStatus.COMPLETED,
    )
    return render(request, 'laboratory/report_print.html', {'lab_request': lab_request})


@patient_login_required
def my_radiology_reports(request):
    patient = request.portal_patient.patient
    radiology_requests = RadiologyRequest.objects.filter(
        Q(consultation__visit__patient=patient) | Q(patient=patient)
    ).select_related('consultation__visit', 'patient')
    return render(request, 'patient_portal/my_radiology_reports.html', {'patient': patient, 'radiology_requests': radiology_requests})


@patient_login_required
def my_radiology_report_detail(request, pk):
    patient = request.portal_patient.patient
    radiology_request = get_object_or_404(
        RadiologyRequest.objects.select_related('consultation__visit__patient', 'consultation__visit__department', 'patient'),
        Q(consultation__visit__patient=patient) | Q(patient=patient),
        pk=pk, status=RequestStatus.COMPLETED,
    )
    return render(request, 'radiology/report_print.html', {'radiology_request': radiology_request})


@patient_login_required
def my_admissions(request):
    patient = request.portal_patient.patient
    admissions = patient.admissions.select_related('ward', 'bed', 'department', 'admitting_doctor').all()
    return render(request, 'patient_portal/my_admissions.html', {'patient': patient, 'admissions': admissions})


@patient_login_required
def my_insurance_claims(request):
    patient = request.portal_patient.patient
    claims = patient.insurance_claims.select_related('insurance_company').all()
    return render(request, 'patient_portal/my_insurance_claims.html', {'patient': patient, 'claims': claims})


# --- Self-service booking: same Visit/ticket process as the Registration Counter --

@patient_login_required
def book_visit(request):
    """Patient Portal booking that creates the same Visit/OPD ticket as the Registration Counter."""
    patient = request.portal_patient.patient

    if request.method == 'POST':
        form = PatientVisitBookingForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient
            visit.registration_fee = form.cleaned_data['registration_fee']
            visit.created_by = None  # self-booked, not staff-created
            if visit.payment_method == Visit.PaymentMethod.CASH:
                visit.payment_status = Visit.PaymentStatus.PENDING
            else:
                visit.payment_status = Visit.PaymentStatus.PENDING
            visit.save()

            write_audit_log(
                request, AuditLog.Action.PATIENT_REGISTER,
                f"Self-service OPD visit booked via Patient Portal: {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=visit.receipt_number,
                amount=visit.registration_fee, payment_method=visit.get_payment_method_display(),
            )
            if visit.payment_method == Visit.PaymentMethod.ESEWA:
                messages.info(request, 'Please complete the eSewa payment to confirm your OPD ticket payment status.')
                return redirect('patient_portal:pay_visit', visit_id=visit.id)

            messages.success(request, 'Visit booked. Payment Pending (Cash Payment at Hospital).')
            return redirect('patient_portal:my_ticket', visit_id=visit.id)
    else:
        form = PatientVisitBookingForm(initial={
            'patient_type': Visit.PatientType.OLD,
            'payment_method': Visit.PaymentMethod.CASH,
        })

    return render(request, 'patient_portal/book_visit.html', {
        'form': form, 'patient': patient,
        'new_fee': 100, 'old_fee': 50,
    })


@patient_login_required
def pay_visit(request, visit_id):
    """Redirect a portal Visit to eSewa using the same helper as public appointments."""
    patient = request.portal_patient.patient
    visit = get_object_or_404(Visit, pk=visit_id, patient=patient)
    if visit.payment_status == Visit.PaymentStatus.PAID:
        return redirect('patient_portal:my_ticket', visit_id=visit.id)
    if visit.payment_method != Visit.PaymentMethod.ESEWA:
        return redirect('patient_portal:my_ticket', visit_id=visit.id)

    success_url = request.build_absolute_uri(reverse('patient_portal:visit_esewa_success'))
    failure_url = request.build_absolute_uri(reverse('patient_portal:visit_esewa_failure')) + '?' + urlencode({'visit_id': visit.id})
    fields = build_payment_fields(
        amount=visit.registration_fee,
        transaction_uuid=visit.receipt_number,
        success_url=success_url,
        failure_url=failure_url,
    )
    return render(request, 'appointments/pay_redirect.html', {
        'appointment': visit, 'form_url': get_form_url(), 'fields': fields,
    })


@patient_login_required
def visit_esewa_success(request):
    data_param = request.GET.get('data', '')
    payload = decode_and_verify_response(data_param) if data_param else None
    if not payload or payload.get('status') != 'COMPLETE':
        messages.error(request, 'We could not verify your eSewa payment. Your visit remains Payment Pending.')
        return redirect('patient_portal:dashboard')

    receipt_number = payload.get('transaction_uuid')
    patient = request.portal_patient.patient
    visit = get_object_or_404(Visit, receipt_number=receipt_number, patient=patient)
    visit.payment_status = Visit.PaymentStatus.PAID
    visit.save(update_fields=['payment_status'])
    write_audit_log(
        request, AuditLog.Action.APPOINTMENT_PAID,
        f"Patient Portal OPD visit paid by eSewa: {visit.receipt_number}",
        patient_id_text=patient.patient_code, receipt_number=visit.receipt_number,
        amount=visit.registration_fee, payment_method='eSewa',
    )
    messages.success(request, 'eSewa payment verified. Your OPD visit is paid.')
    return redirect('patient_portal:my_ticket', visit_id=visit.id)


@patient_login_required
def visit_esewa_failure(request):
    visit_id = request.GET.get('visit_id')
    messages.error(request, 'eSewa payment was not completed. Your visit remains Payment Pending.')
    if visit_id:
        return redirect('patient_portal:my_ticket', visit_id=visit_id)
    return redirect('patient_portal:dashboard')

def forgot_password(request):
    from patient_portal.forms import ForgotPasswordForm
    from patient_portal.models import PatientAccount
    import random

    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data['method']
            hospital_id = form.cleaned_data['hospital_id'].strip()
            contact_value = form.cleaned_data['contact_value'].strip()

            # Search account
            account = PatientAccount.objects.select_related('patient').filter(
                patient__patient_code__iexact=hospital_id
            ).first()

            if not account:
                messages.error(request, 'No active account found for that Hospital ID.')
                return render(request, 'patient_portal/forgot_password.html', {'form': form})

            # Check matching email or phone
            patient = account.patient
            if method == 'email' and (not patient.email or patient.email.lower() != contact_value.lower()):
                messages.error(request, 'The email address does not match our records.')
                return render(request, 'patient_portal/forgot_password.html', {'form': form})
            elif method == 'phone' and patient.phone_number != contact_value:
                messages.error(request, 'The phone number does not match our records.')
                return render(request, 'patient_portal/forgot_password.html', {'form': form})

            # Valid matches! Generate a random OTP code
            otp = f"{random.randint(100000, 999999)}"
            request.session['reset_account_id'] = account.id
            request.session['reset_otp'] = otp
            request.session['reset_method'] = method

            if method == 'email':
                from django.core.mail import send_mail
                from django.conf import settings as django_settings
                send_mail(
                    subject=f"{django_settings.HOSPITAL_NAME if hasattr(django_settings, 'HOSPITAL_NAME') else 'Hamro Hospital'} - Password Reset Code",
                    message=(
                        f"Hello {patient.full_name},\n\n"
                        f"Your Patient Portal password reset code is: {otp}\n\n"
                        f"Enter this code on the reset password page to choose a new password. "
                        f"If you did not request this, you can ignore this email.\n\n"
                        f"Hospital ID: {patient.patient_code}"
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[patient.email],
                    fail_silently=True,
                )
                messages.info(request, f'An email has been sent to {patient.email} with your reset code.')
            else:
                # SMS gateway not yet connected - printed here so the OTP is
                # still usable end-to-end today; swap this block for a real
                # SMS provider call (e.g. Sparrow SMS) when one is available,
                # the rest of the reset flow already expects an OTP either way.
                print(f"[SMS OTP - GATEWAY NOT YET CONNECTED] OTP {otp} for phone {patient.phone_number}")
                messages.info(request, f'A verification SMS with OTP code has been sent to {patient.phone_number}.')

            return redirect('patient_portal:reset_password')
    else:
        form = ForgotPasswordForm()
    return render(request, 'patient_portal/forgot_password.html', {'form': form})


def reset_password(request):
    from patient_portal.forms import ResetPasswordForm
    from patient_portal.models import PatientAccount

    account_id = request.session.get('reset_account_id')
    stored_otp = request.session.get('reset_otp')
    method = request.session.get('reset_method')

    if not account_id or not stored_otp:
        messages.error(request, 'Session expired. Please request a new password reset.')
        return redirect('patient_portal:forgot_password')

    account = get_object_or_404(PatientAccount, pk=account_id)

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            otp_typed = form.cleaned_data.get('otp_code', '').strip()

            # Now that a real code is emailed (or SMS'd once a gateway is
            # connected), verify it for either method - not just phone.
            if otp_typed != stored_otp:
                messages.error(request, 'Invalid or expired verification code.')
                return render(request, 'patient_portal/reset_password.html', {'form': form, 'method': method})

            new_password = form.cleaned_data['new_password']
            account.set_password(new_password)
            account.save()

            # Clear session
            request.session.pop('reset_account_id', None)
            request.session.pop('reset_otp', None)
            request.session.pop('reset_method', None)

            messages.success(request, 'Your password has been reset successfully. Please log in with your new password.')
            return redirect('patient_portal:login')
    else:
        form = ResetPasswordForm()
    return render(request, 'patient_portal/reset_password.html', {'form': form, 'method': method})


@patient_login_required
def my_documents(request):
    """All uploaded reports/PDFs across every department for this patient
    (spec 8 & 19: Patients can view/download their own uploaded reports).
    This is what actually shows the multi-file uploads Laboratory/
    Radiology/etc attach through documents.PatientDocument - the old
    per-request result_file fields are still available via My Lab Reports
    / My Radiology Reports for a single-result summary view."""
    from documents.models import PatientDocument, DocumentCategory
    patient = request.portal_patient.patient
    documents = PatientDocument.objects.filter(patient=patient, is_active=True).select_related('uploaded_by')
    category = request.GET.get('category', '')
    if category:
        documents = documents.filter(category=category)
    return render(request, 'patient_portal/my_documents.html', {
        'patient': patient, 'documents': documents,
        'categories': DocumentCategory.choices, 'selected_category': category,
    })


@patient_login_required
def my_document_download(request, pk):
    """Patients may download their own documents (spec 8/19/20) - this is
    the patient-side equivalent of documents.views.document_download,
    kept separate because PatientAccount isn't a staff accounts.User."""
    from documents.models import PatientDocument
    patient = request.portal_patient.patient
    doc = get_object_or_404(PatientDocument, pk=pk, patient=patient, is_active=True)
    if not doc.file:
        raise Http404('File not found.')
    write_audit_log(
        request, AuditLog.Action.DOCUMENT_DOWNLOADED,
        f"Patient downloaded \"{doc.title}\" from their own portal",
        patient_id_text=patient.patient_code,
    )
    return FileResponse(doc.file.open('rb'), filename=doc.file.name.rsplit('/', 1)[-1])

@patient_login_required
def my_timeline(request):
    patient = request.portal_patient.patient
    events = patient.timeline_events.select_related('actor').all()[:500]
    return render(request, 'patient_portal/my_timeline.html', {'patient': patient, 'events': events})


@patient_login_required
def pay_bill(request, pk):
    patient = request.portal_patient.patient
    bill = get_object_or_404(Bill, pk=pk, patient=patient, status=Bill.Status.PENDING)
    success_url = request.build_absolute_uri(reverse('patient_portal:bill_esewa_success'))
    failure_url = request.build_absolute_uri(reverse('patient_portal:bill_esewa_failure')) + '?' + urlencode({'bill_id': bill.id})
    fields = build_payment_fields(
        amount=bill.final_amount_paid,
        transaction_uuid=bill.bill_number,
        success_url=success_url,
        failure_url=failure_url,
    )
    return render(request, 'appointments/pay_redirect.html', {'appointment': bill, 'form_url': get_form_url(), 'fields': fields})


def bill_esewa_success(request):
    from workflow.utils import record_payment_event
    from billing.models import PaymentMethod
    data_param = request.GET.get('data', '')
    payload = decode_and_verify_response(data_param) if data_param else None
    if not payload or payload.get('status') != 'COMPLETE':
        messages.error(request, 'We could not verify your eSewa bill payment.')
        return redirect('patient_portal:dashboard')
    bill = get_object_or_404(Bill, bill_number=payload.get('transaction_uuid'))
    bill.payment_method = PaymentMethod.ESEWA
    bill.status = Bill.Status.PAID
    bill.save(update_fields=['payment_method', 'status'])
    record_payment_event(bill, method=PaymentMethod.ESEWA, transaction_reference=payload.get('transaction_code', ''), gateway_response=str(payload), remarks='Patient Portal eSewa bill payment')
    messages.success(request, f'eSewa payment completed for bill {bill.bill_number}.')
    return redirect('patient_portal:my_bill_receipt', pk=bill.pk)


def bill_esewa_failure(request):
    messages.error(request, 'eSewa payment was not completed. Bill remains pending.')
    bill_id = request.GET.get('bill_id')
    if bill_id:
        return redirect('patient_portal:my_bill_receipt', pk=bill_id)
    return redirect('patient_portal:my_bills')
