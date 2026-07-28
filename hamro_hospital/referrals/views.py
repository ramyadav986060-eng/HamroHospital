from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role
from accounts.utils import create_notification
from patients.models import Patient
from referrals.forms import ReferralForm
from referrals.models import Referral
from billing.models import Bill, BillItem
from website.models import HospitalService




def _bill_type_for_referral(referral):
    return {
        Referral.ReferralType.LABORATORY: 'lab',
        Referral.ReferralType.RADIOLOGY: 'radiology',
        Referral.ReferralType.PHARMACY: 'pharmacy',
        Referral.ReferralType.OPERATION_THEATRE: 'surgery',
        Referral.ReferralType.BLOOD_BANK: 'blood_bank',
        Referral.ReferralType.ADMISSION: 'ipd',
    }.get(referral.referral_type, 'other')


def _service_price_for_item(name):
    svc = HospitalService.objects.filter(name__iexact=name, is_active=True).first() or HospitalService.objects.filter(name__icontains=name, is_active=True).first()
    if svc:
        return svc, svc.price
    return None, 0

REFERRAL_ROLE_MAP = {
    Referral.ReferralType.LABORATORY: Role.LABORATORY,
    Referral.ReferralType.RADIOLOGY: Role.RADIOLOGY,
    Referral.ReferralType.PHARMACY: Role.PHARMACY,
    Referral.ReferralType.NURSING: Role.NURSING,
    Referral.ReferralType.ADMISSION: Role.WARD_ADMISSION,
    Referral.ReferralType.OPERATION_THEATRE: Role.OPERATION_THEATRE,
    Referral.ReferralType.BLOOD_BANK: Role.BLOOD_BANK,
}


def _role_referral_type(user):
    role = getattr(user, 'effective_role', getattr(user, 'role', ''))
    reverse_map = {v: k for k, v in REFERRAL_ROLE_MAP.items()}
    return reverse_map.get(role)


@login_required
@role_required(Role.DOCTOR, Role.SUPER_ADMIN)
def referral_create(request, patient_id=None, referral_type=None):
    initial_data = {}
    if patient_id:
        initial_data['patient'] = get_object_or_404(Patient, pk=patient_id)
    if referral_type:
        initial_data['referral_type'] = referral_type
    elif request.method == 'GET' and patient_id:
        return render(request, 'referrals/category_select.html', {'patient': initial_data['patient'], 'types': Referral.ReferralType.choices})

    if request.method == 'POST':
        form = ReferralForm(request.POST, request.FILES)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.created_by = request.user
            if hasattr(request.user, 'doctor_profile'):
                referral.referred_by = request.user.doctor_profile
            referral.save()
            url = reverse('referrals:referral_detail', args=[referral.pk])
            target_role = REFERRAL_ROLE_MAP.get(referral.referral_type)
            if target_role:
                create_notification(
                    title='New Doctor Referral',
                    message=f'{referral.patient.full_name} has been referred to {referral.get_referral_type_display()}.',
                    role=target_role,
                    related_url=url,
                )
            elif referral.to_department_id:
                for doc in referral.to_department.doctors.select_related('user_account').filter(is_active=True, user_account__isnull=False):
                    create_notification(
                        title='New Department Referral',
                        message=f'{referral.patient.full_name} referred to {referral.to_department.name}. Reason: {referral.reason[:80]}',
                        user=doc.user_account,
                        related_url=url,
                    )
            messages.success(request, 'Referral submitted and destination department notified.')
            return redirect('referrals:referral_detail', pk=referral.pk)
    else:
        form = ReferralForm(initial=initial_data)

    return render(request, 'referrals/referral_form.html', {'form': form})


@login_required
def department_queue(request):
    referrals = Referral.objects.select_related('patient', 'referred_by', 'to_department').all()
    role_type = _role_referral_type(request.user)
    if role_type and not request.user.is_superuser:
        referrals = referrals.filter(referral_type=role_type)

    status_filter = request.GET.get('status')
    if status_filter in dict(Referral.STATUS_CHOICES):
        referrals = referrals.filter(status=status_filter)

    return render(request, 'referrals/queue.html', {
        'referrals': referrals.order_by('-created_at'),
        'statuses': Referral.STATUS_CHOICES,
        'selected_status': status_filter or '',
    })


@login_required
def referral_detail(request, pk):
    referral = get_object_or_404(Referral.objects.select_related('patient', 'referred_by', 'to_department'), pk=pk)
    return render(request, 'referrals/referral_detail.html', {'referral': referral})


@login_required
def referral_update_status(request, pk):
    referral = get_object_or_404(Referral, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Referral.STATUS_CHOICES):
            if new_status == 'acknowledged':
                referral.acknowledge(request.user)
            elif new_status == 'completed':
                referral.complete(request.user)
            else:
                referral.status = new_status
                referral.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Referral status updated to {referral.get_status_display()}.')
    return redirect('referrals:referral_detail', pk=referral.pk)


@login_required
def referral_generate_bill(request, pk):
    referral = get_object_or_404(Referral.objects.select_related('patient'), pk=pk)
    if referral.related_bill_id:
        return redirect('billing:receipt', pk=referral.related_bill_id)
    if request.method == 'POST':
        bill = Bill.objects.create(
            patient=referral.patient,
            cashier=request.user if request.user.is_authenticated else None,
            bill_type=_bill_type_for_referral(referral),
            counter_name=f'{referral.get_referral_type_display()} Counter',
            payment_method=request.POST.get('payment_method') or 'cash',
            status=Bill.Status.PENDING,
        )
        items = [line.strip() for line in (referral.requested_items or referral.reason).splitlines() if line.strip()]
        if not items:
            items = [referral.get_referral_type_display()]
        for item in items:
            svc, price = _service_price_for_item(item)
            BillItem.objects.create(bill=bill, service=svc, service_name=item, unit_price=price, quantity=1)
        bill.recalculate_total()
        referral.related_bill = bill
        if referral.status == 'new':
            referral.acknowledge(request.user)
        referral.save(update_fields=['related_bill'])
        create_notification(
            title='Pending Bill Generated',
            message=f'Pending bill {bill.bill_number} generated for {referral.patient.full_name}.',
            role=Role.CASH_COUNTER,
            related_url=reverse('billing:receipt', args=[bill.pk]),
        )
        messages.success(request, f'Pending bill {bill.bill_number} generated. Print and send patient to Cash Counter or eSewa.')
        return redirect('billing:receipt', pk=bill.pk)
    return redirect('referrals:referral_detail', pk=referral.pk)
