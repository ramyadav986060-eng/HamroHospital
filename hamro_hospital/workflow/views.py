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
        if user_role == Role.DEPARTMENT_HEAD and request.user.department_id:
            orders = orders.filter(destination_department=request.user.department)
        elif service_type:
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

@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD, Role.LABORATORY, Role.RADIOLOGY, Role.PHARMACY, Role.WARD_ADMISSION, Role.OPERATION_THEATRE, Role.BLOOD_BANK)
def department_revenue(request):
    from django.db.models import Sum, Count
    from django.utils import timezone
    import datetime

    today = timezone.now().date()
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    events = PaymentEvent.objects.select_related('bill', 'bill__patient')
    if start:
        try:
            events = events.filter(paid_at__date__gte=datetime.date.fromisoformat(start))
        except ValueError:
            pass
    else:
        events = events.filter(paid_at__date=today)
    if end:
        try:
            events = events.filter(paid_at__date__lte=datetime.date.fromisoformat(end))
        except ValueError:
            pass

    orders = ServiceOrder.objects.filter(bill__payment_events__in=events).select_related('bill').distinct()
    role_type = ROLE_SERVICE_TYPES.get(request.user.effective_role)
    if request.user.effective_role == Role.DEPARTMENT_HEAD and request.user.department_id and not request.user.is_superuser:
        orders = orders.filter(destination_department=request.user.department)
    elif role_type and not request.user.is_superuser and request.user.effective_role != Role.ACCOUNTS_DEPT:
        orders = orders.filter(service_type=role_type)
    summary = orders.values('service_type').annotate(total=Sum('bill__payment_events__amount'), count=Count('id')).order_by('service_type')
    return render(request, 'workflow/department_revenue.html', {
        'summary': summary,
        'orders': orders[:300],
        'start_date': start,
        'end_date': end,
    })
