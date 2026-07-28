from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode

from accounts.models import AuditLog
from accounts.utils import write_audit_log
from appointments.esewa import build_payment_fields, get_form_url, decode_and_verify_response
from appointments.forms import AppointmentForm
from appointments.models import Appointment


def book_appointment(request):
    """Public online appointment booking form."""
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.registration_fee = form.cleaned_data['registration_fee']
            if appointment.payment_method == Appointment.PaymentMethod.CASH:
                from appointments.models import _generate_appointment_number
                appointment.payment_status = Appointment.PaymentStatus.PENDING
                appointment.appointment_number = _generate_appointment_number()
                appointment.save()
                appointment._generate_qr_code()
                appointment._generate_barcode()
                
                write_audit_log(
                    request, AuditLog.Action.APPOINTMENT_BOOKED,
                    f"Appointment booked with Cash (Pending Payment): {appointment.appointment_number}",
                    receipt_number=appointment.appointment_number,
                )
                messages.success(request, 'Appointment booked successfully. Payment is pending at Registration Counter.')
                return redirect('appointments:receipt', transaction_uuid=appointment.transaction_uuid)
            else:
                appointment.save()
                return redirect('appointments:pay', transaction_uuid=appointment.transaction_uuid)
    else:
        initial = {}
        department_id = request.GET.get('department')
        if department_id and department_id.isdigit():
            initial['department'] = department_id
        doctor_id = request.GET.get('doctor')
        if doctor_id and doctor_id.isdigit():
            initial['doctor'] = doctor_id
        form = AppointmentForm(initial=initial)
    return render(request, 'appointments/book_appointment.html', {
        'form': form, 'new_fee': settings.NEW_PATIENT_REGISTRATION_FEE, 'old_fee': settings.OLD_PATIENT_REGISTRATION_FEE,
    })


def pay_appointment(request, transaction_uuid):
    """
    Shows checkout or gateway redirection for online appointment bookings.
    Supports eSewa and other mock-verified digital payment channels of Nepal (Khalti, Card, Bank, etc.).
    """
    appointment = get_object_or_404(Appointment, transaction_uuid=transaction_uuid)
    if appointment.payment_status == Appointment.PaymentStatus.PAID:
        return redirect('appointments:receipt', transaction_uuid=appointment.transaction_uuid)

    # 1. Modular eSewa flow
    if appointment.payment_method == Appointment.PaymentMethod.ESEWA:
        success_url = request.build_absolute_uri(reverse('appointments:esewa_success'))
        failure_url = request.build_absolute_uri(reverse('appointments:esewa_failure')) + '?' + urlencode(
            {'transaction_uuid': str(appointment.transaction_uuid)}
        )

        fields = build_payment_fields(
            amount=appointment.registration_fee,
            transaction_uuid=appointment.transaction_uuid,
            success_url=success_url,
            failure_url=failure_url,
        )

        return render(request, 'appointments/pay_redirect.html', {
            'appointment': appointment, 'form_url': get_form_url(), 'fields': fields,
        })
        
    # 2. General online gateway mock simulation (Khalti, FonePay, Cards, Mobile Banking, etc.)
    if request.method == 'POST':
        import random
        import datetime
        from appointments.models import _generate_appointment_number

        # Auto-verify payment
        appointment.payment_status = Appointment.PaymentStatus.PAID
        appointment.esewa_ref_id = f"TXN-{appointment.payment_method.upper()}-{random.randint(100000, 999999)}"
        appointment.paid_at = datetime.datetime.now()
        appointment.appointment_number = _generate_appointment_number()
        appointment.save()
        appointment._generate_qr_code()
        appointment._generate_barcode()

        write_audit_log(
            request, AuditLog.Action.APPOINTMENT_PAID,
            f"Online appointment paid ({appointment.get_payment_method_display()}): {appointment.appointment_number}",
            patient_id_text='', receipt_number=appointment.appointment_number,
            amount=appointment.registration_fee, payment_method=appointment.get_payment_method_display(),
        )

        messages.success(request, f'Payment verified successfully via {appointment.get_payment_method_display()}!')
        return redirect('appointments:receipt', transaction_uuid=appointment.transaction_uuid)

    return render(request, 'appointments/online_pay_simulate.html', {
        'appointment': appointment,
    })


def esewa_success(request):
    """
    eSewa redirects here after a successful payment with ?data=<base64 json>.
    We verify the signature, confirm status, then credit the appointment.
    """
    data_param = request.GET.get('data', '')
    payload = decode_and_verify_response(data_param) if data_param else None

    if not payload or payload.get('status') != 'COMPLETE':
        messages.error(request, 'We could not verify your eSewa payment. Please try again or contact the hospital.')
        return redirect('appointments:book_appointment')

    transaction_uuid = payload.get('transaction_uuid')
    appointment = get_object_or_404(Appointment, transaction_uuid=transaction_uuid)
    appointment.mark_paid(esewa_ref_id=payload.get('transaction_code', ''))

    write_audit_log(
        request, AuditLog.Action.APPOINTMENT_PAID,
        f"Online appointment paid: {appointment.appointment_number}",
        patient_id_text='', receipt_number=appointment.appointment_number,
        amount=appointment.registration_fee, payment_method='eSewa',
    )
    write_audit_log(
        request, AuditLog.Action.APPOINTMENT_BOOKED,
        f"Appointment booked online by {appointment.full_name}",
        receipt_number=appointment.appointment_number,
    )

    return redirect('appointments:receipt', transaction_uuid=appointment.transaction_uuid)


def esewa_failure(request):
    transaction_uuid = request.GET.get('transaction_uuid')
    appointment = None
    if transaction_uuid:
        appointment = Appointment.objects.filter(transaction_uuid=transaction_uuid).first()
        if appointment:
            appointment.mark_failed()
    return render(request, 'appointments/payment_failed.html', {'appointment': appointment})


def appointment_receipt(request, transaction_uuid):
    appointment = get_object_or_404(
        Appointment.objects.select_related('department', 'doctor', 'district'),
        transaction_uuid=transaction_uuid,
    )
    # Allow viewing if it is Cash (which is initially pending) or if it has been Paid!
    if appointment.payment_method != Appointment.PaymentMethod.CASH and appointment.payment_status != Appointment.PaymentStatus.PAID:
        return redirect('appointments:pay', transaction_uuid=appointment.transaction_uuid)
    return render(request, 'appointments/receipt.html', {'appointment': appointment})
