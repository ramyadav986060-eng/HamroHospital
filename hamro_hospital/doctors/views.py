from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required, doctor_required
from doctors.models import Doctor
from doctors.forms import DoctorForm, DoctorProfileForm
from patients.models import Patient, Visit
from referrals.models import Referral


@super_admin_required
def doctor_list(request):
    doctors = Doctor.objects.select_related('department', 'user_account').all()
    return render(request, 'doctors/doctor_list.html', {'doctors': doctors})


@super_admin_required
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save()
            if form.generated_credentials:
                username, password = form.generated_credentials
                messages.success(request, f'Doctor "{doctor.full_name}" added. Login: {username} / {password}')
            else:
                messages.success(request, f'Doctor "{doctor.full_name}" added.')
            return redirect('doctors:doctor_list')
    else:
        form = DoctorForm()
    return render(request, 'doctors/doctor_form.html', {'form': form, 'title': 'Add Doctor'})


@super_admin_required
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            if form.generated_credentials:
                username, password = form.generated_credentials
                messages.success(request, f'Doctor "{doctor.full_name}" updated. Login: {username} / {password}')
            else:
                messages.success(request, f'Doctor "{doctor.full_name}" updated.')
            return redirect('doctors:doctor_list')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'doctors/doctor_form.html', {
        'form': form, 'title': f'Edit Dr. {doctor.full_name}', 'doctor': doctor,
    })


@super_admin_required
def doctor_delete(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        name = doctor.full_name
        doctor.is_active = False
        doctor.save(update_fields=['is_active'])
        if doctor.user_account_id:
            doctor.user_account.is_active_staff = False
            doctor.user_account.save(update_fields=['is_active_staff'])
        messages.success(request, f'Dr. {name} has been deactivated (kept for historical visit records).')
        return redirect('doctors:doctor_list')
    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})


@doctor_required
def doctor_dashboard(request):
    doctor_profile = getattr(request.user, 'doctor_profile', None)
    todays_visits = 0
    todays_queue = Visit.objects.none()
    recent_referrals = Referral.objects.none()
    if doctor_profile:
        import datetime
        todays_queue = Visit.objects.filter(doctor=doctor_profile, visit_date=datetime.date.today()).select_related('patient', 'department')[:20]
        todays_visits = todays_queue.count()
        recent_referrals = Referral.objects.filter(referred_by=doctor_profile).select_related('patient', 'to_department')[:10]

    return render(request, 'doctors/dashboard.html', {
        'doctor_profile': doctor_profile,
        'todays_visits': todays_visits,
        'todays_queue': todays_queue,
        'recent_referrals': recent_referrals,
    })


@doctor_required
def doctor_patient_search(request):
    q = request.GET.get('q', '').strip()
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).select_related('district')[:50]
    return render(request, 'doctors/patient_search.html', {'q': q, 'patients': patients})


@doctor_required
def doctor_profile(request):
    doctor = getattr(request.user, 'doctor_profile', None)
    if not doctor:
        messages.error(request, 'Your staff account is not linked to a Doctor profile yet.')
        return redirect('doctors:dashboard')
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('doctors:profile')
    else:
        form = DoctorProfileForm(instance=doctor)
    return render(request, 'doctors/profile.html', {'form': form, 'doctor_profile': doctor})


@doctor_required
def doctor_change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('doctors:profile')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    return render(request, 'doctors/change_password.html', {'form': form})
