from decimal import Decimal

from django.urls import reverse
from django.utils import timezone


def add_timeline(patient, event_type, title, description='', actor=None, related_url='', source=None):
    from workflow.models import PatientTimeline
    kwargs = {}
    if source is not None:
        kwargs = {
            'source_app': source._meta.app_label,
            'source_model': source._meta.model_name,
            'source_object_id': source.pk,
        }
    return PatientTimeline.objects.create(
        patient=patient,
        event_type=event_type,
        title=title,
        description=description,
        actor=actor,
        related_url=related_url,
        **kwargs,
    )


def service_type_from_referral(referral):
    from workflow.models import ServiceOrder
    return {
        'laboratory': ServiceOrder.ServiceType.LABORATORY,
        'radiology': ServiceOrder.ServiceType.RADIOLOGY,
        'pharmacy': ServiceOrder.ServiceType.PHARMACY,
        'admission': ServiceOrder.ServiceType.ADMISSION,
        'nursing': ServiceOrder.ServiceType.NURSING,
        'operation_theatre': ServiceOrder.ServiceType.OPERATION_THEATRE,
        'blood_bank': ServiceOrder.ServiceType.BLOOD_BANK,
    }.get(referral.referral_type, ServiceOrder.ServiceType.OTHER)


def create_orders_for_referral(referral, actor=None):
    from workflow.models import ServiceOrder, PatientTimeline
    from referrals.models import Referral
    from website.models import HospitalService

    items = [line.strip() for line in (referral.requested_items or '').splitlines() if line.strip()]
    if not items:
        items = [referral.get_referral_type_display()]
    orders = []
    for item in items:
        svc = HospitalService.objects.filter(name__iexact=item, is_active=True).first() or HospitalService.objects.filter(name__icontains=item, is_active=True).first()
        price = svc.price if svc else Decimal('0')
        order, _created = ServiceOrder.objects.get_or_create(
            referral=referral,
            patient=referral.patient,
            service_name=item,
            defaults={
                'ordered_by': actor or referral.created_by,
                'source_role': getattr(actor or referral.created_by, 'role', '') or '',
                'destination_role': referral.referral_type,
                'destination_department': referral.to_department,
                'service_type': service_type_from_referral(referral),
                'unit_price': price,
                'quantity': 1,
                'status': ServiceOrder.Status.REQUESTED,
                'payment_status': ServiceOrder.PaymentStatus.PENDING,
                'notes': referral.reason,
            },
        )
        orders.append(order)
    add_timeline(
        referral.patient,
        PatientTimeline.EventType.REFERRAL,
        f'Referral created: {referral.get_referral_type_display()}',
        referral.reason,
        actor=actor or referral.created_by,
        related_url=reverse('referrals:referral_detail', args=[referral.pk]),
        source=referral,
    )
    return orders


def record_payment_event(bill, amount=None, method=None, received_by=None, transaction_reference='', gateway_response='', remarks=''):
    from workflow.models import PaymentEvent, PatientTimeline
    amount = amount if amount is not None else bill.final_amount_paid
    method = method or bill.payment_method
    event = PaymentEvent.objects.create(
        bill=bill,
        amount=amount,
        payment_method=method,
        received_by=received_by,
        transaction_reference=transaction_reference,
        gateway_response=gateway_response,
        remarks=remarks,
        paid_at=timezone.now(),
    )
    bill.service_orders.update(payment_status='paid', status='paid')
    add_timeline(
        bill.patient,
        PatientTimeline.EventType.PAYMENT,
        f'Payment completed: {bill.bill_number}',
        f'NPR {amount} via {method}',
        actor=received_by,
        related_url=reverse('billing:receipt', args=[bill.pk]),
        source=bill,
    )
    return event
