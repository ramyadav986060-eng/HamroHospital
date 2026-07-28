from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Referral
from .forms import ReferralForm
from patients.models import Patient
from accounts.decorators import role_required
from accounts.models import Role

@login_required
@role_required(Role.DOCTOR, Role.SUPER_ADMIN)
def referral_create(request, patient_id=None):
    initial_data = {}
    if patient_id:
        initial_data['patient'] = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        form = ReferralForm(request.POST)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.created_by = request.user
            if hasattr(request.user, 'doctor_profile'):
                referral.referred_by = request.user.doctor_profile
            referral.save()
            messages.success(request, 'Referral created successfully.')
            return redirect('doctors:dashboard')
    else:
        form = ReferralForm(initial=initial_data)
    
    return render(request, 'referrals/referral_form.html', {'form': form})

@login_required
def department_queue(request):
    # Queue for the department
    referrals = Referral.objects.all().order_by('-created_at')
    
    # Optional filtering by status
    status_filter = request.GET.get('status')
    if status_filter in dict(Referral.STATUS_CHOICES):
        referrals = referrals.filter(status=status_filter)

    return render(request, 'referrals/queue.html', {'referrals': referrals})

@login_required
def referral_update_status(request, pk):
    referral = get_object_or_404(Referral, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Referral.STATUS_CHOICES):
            referral.status = new_status
            referral.save()
            messages.success(request, f'Referral status updated to {referral.get_status_display()}.')
    return redirect('referrals:department_queue')
