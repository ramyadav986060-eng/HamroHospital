from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import role_required
from accounts.models import Role
from workflow.models import ServiceOrder, PatientTimeline, PaymentEvent


ROLE_SERVICE_TYPES = {
    Role.LABORATORY: ServiceOrder.ServiceType.LABORATORY,
    Role.RADIOLOGY: ServiceOrder.ServiceType.RADIOLOGY,
    Role.PHARMACY: ServiceOrder.ServiceType.PHARMACY,
    Role.WARD_ADMISSION: ServiceOrder.ServiceType.ADMISSION,
    Role.NURSING: ServiceOrder.ServiceType.NURSING,
    Role.OPERATION_THEATRE: ServiceOrder.ServiceType.OPERATION_THEATRE,
    Role.BLOOD_BANK: ServiceOrder.ServiceType.BLOOD_BANK,
}


@role_required(*Role.values)
def service_order_queue(request):
    orders = ServiceOrder.objects.select_related('patient', 'ordered_by', 'destination_department', 'bill', 'referral')
    user_role = request.user.effective_role
    if not request.user.is_superuser and user_role not in [Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT]:
        service_type = ROLE_SERVICE_TYPES.get(user_role)
        if service_type:
            orders = orders.filter(service_type=service_type)
        elif user_role == Role.DOCTOR and hasattr(request.user, 'doctor_profile'):
            orders = orders.filter(ordered_by=request.user)
        else:
            orders = orders.none()

    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    q = request.GET.get('q', '').strip()
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if q:
        from django.db.models import Q
        orders = orders.filter(
            Q(patient__patient_code__icontains=q) |
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q) |
            Q(patient__phone_number__icontains=q) |
            Q(service_name__icontains=q) |
            Q(bill__bill_number__icontains=q)
        )
    paginator = Paginator(orders, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'workflow/service_order_queue.html', {
        'page_obj': page_obj,
        'statuses': ServiceOrder.Status.choices,
        'payment_statuses': ServiceOrder.PaymentStatus.choices,
        'selected_status': status,
        'selected_payment_status': payment_status,
        'q': q,
    })


@role_required(*Role.values)
def service_order_detail(request, pk):
    order = get_object_or_404(ServiceOrder.objects.select_related('patient', 'ordered_by', 'destination_department', 'bill', 'referral'), pk=pk)
    return render(request, 'workflow/service_order_detail.html', {'order': order})


@role_required(*Role.values)
def service_order_update(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(ServiceOrder.Status.choices):
            if new_status == ServiceOrder.Status.ACCEPTED:
                order.mark_accepted()
            elif new_status == ServiceOrder.Status.COMPLETED:
                order.mark_completed()
            else:
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Service order status updated.')
    return redirect('workflow:service_order_detail', pk=order.pk)


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def payment_events(request):
    events = PaymentEvent.objects.select_related('bill', 'bill__patient', 'received_by').all()
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        events = events.filter(
            Q(bill__bill_number__icontains=q) |
            Q(bill__patient__patient_code__icontains=q) |
            Q(transaction_reference__icontains=q)
        )
    paginator = Paginator(events, 25)
    return render(request, 'workflow/payment_events.html', {'page_obj': paginator.get_page(request.GET.get('page')), 'q': q})


@role_required(*Role.values)
def patient_timeline(request, patient_id):
    from patients.models import Patient
    patient = get_object_or_404(Patient, pk=patient_id)
    events = patient.timeline_events.select_related('actor').all()
    paginator = Paginator(events, 40)
    return render(request, 'workflow/patient_timeline.html', {'patient': patient, 'page_obj': paginator.get_page(request.GET.get('page'))})
