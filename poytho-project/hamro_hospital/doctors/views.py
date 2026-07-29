from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required, doctor_required, role_required
from accounts.models import Role
from doctors.models import Doctor
from doctors.forms import DoctorForm, DoctorProfileForm
from patients.models import Patient, Visit
from referrals.models import Referral


def ensure_doctor_profile_for_user(user):
    """Guarantee active Doctor-role users have a linked Doctor profile.

    This prevents doctor dashboards/profile pages from showing a broken
    "not linked" warning after staff account creation.
    """
    if getattr(user, 'role', '') != 'doctor' and not getattr(user, 'is_superuser', False):
        return getattr(user, 'doctor_profile', None)
    profile = getattr(user, 'doctor_profile', None)
    if profile:
        return profile
    from departments.models import Department
    dept = getattr(user, 'department', None) or Department.objects.filter(is_active=True).first()
    if not dept:
        return None
    full_name = user.get_full_name() or user.username
    return Doctor.objects.create(
        user_account=user,
        department=dept,
        full_name=full_name,
        qualification='Not specified',
        specialization=getattr(user, 'designation', '') or 'General',
        consultation_fee=0,
        contact_number=getattr(user, 'phone_number', ''),
        is_active=True,
    )


@role_required(Role.SUPER_ADMIN, Role.DEPARTMENT_HEAD)
def doctor_list(request):
    doctors = Doctor.objects.select_related('department', 'user_account').all()
    if request.user.effective_role == Role.DEPARTMENT_HEAD and not request.user.is_superuser:
        doctors = doctors.filter(department=request.user.department)
    q = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()
    if q:
        doctors = doctors.filter(Q(full_name__icontains=q) | Q(specialization__icontains=q) | Q(qualification__icontains=q) | Q(department__name__icontains=q))
    if department_id:
        doctors = doctors.filter(department_id=department_id)
    from departments.models import Department
    departments = Department.objects.filter(is_active=True).order_by('name')
    if request.user.effective_role == Role.DEPARTMENT_HEAD and not request.user.is_superuser:
        departments = departments.filter(pk=request.user.department_id)
    return render(request, 'doctors/doctor_list.html', {'doctors': doctors, 'departments': departments, 'q': q, 'selected_department': department_id})


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


@role_required(Role.SUPER_ADMIN, Role.DEPARTMENT_HEAD)
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    is_department_head = request.user.effective_role == Role.DEPARTMENT_HEAD and not request.user.is_superuser
    if is_department_head and (not request.user.department_id or doctor.department_id != request.user.department_id):
        messages.error(request, 'Department Heads can only manage doctor schedules in their own department.')
        return redirect('doctors:doctor_list')
    form_class = DoctorProfileForm if is_department_head else DoctorForm
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            if getattr(form, 'generated_credentials', None):
                username, password = form.generated_credentials
                messages.success(request, f'Doctor "{doctor.full_name}" updated. Login: {username} / {password}')
            else:
                messages.success(request, f'Doctor "{doctor.full_name}" updated.')
            return redirect('doctors:doctor_list')
    else:
        form = form_class(instance=doctor)
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
    doctor_profile = ensure_doctor_profile_for_user(request.user)
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
def doctor_opd_visits(request):
    doctor_profile = ensure_doctor_profile_for_user(request.user)
    import datetime
    selected_date = request.GET.get('date') or datetime.date.today().isoformat()
    q = (request.GET.get('q') or '').strip()
    try:
        date_obj = datetime.date.fromisoformat(selected_date)
    except ValueError:
        date_obj = datetime.date.today()
    visits = Visit.objects.filter(doctor=doctor_profile, visit_date=date_obj).select_related('patient', 'department') if doctor_profile else Visit.objects.none()
    if q:
        visits = visits.filter(Q(patient__patient_code__icontains=q) | Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q) | Q(patient__phone_number__icontains=q) | Q(receipt_number__icontains=q))
    return render(request, 'doctors/opd_visits.html', {'doctor_profile': doctor_profile, 'visits': visits, 'selected_date': date_obj, 'q': q})


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
    doctor = ensure_doctor_profile_for_user(request.user)
    if not doctor:
        messages.error(request, 'Doctor profile setup is incomplete. Please contact Super Admin.')
        return redirect('doctors:dashboard')
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            # Keep the linked staff account's visible staff photo/contact aligned where possible.
            if doctor.user_account_id:
                staff = doctor.user_account
                staff.phone_number = doctor.contact_number or staff.phone_number
                if doctor.photo and not staff.staff_photo:
                    staff.staff_photo = doctor.photo
                staff.save(update_fields=['phone_number', 'staff_photo'])
            messages.success(request, 'Profile updated successfully.')
            return redirect('doctors:profile')
    else:
        form = DoctorProfileForm(instance=doctor)

    staff_user = doctor.user_account or request.user
    completion_fields = [doctor.full_name, doctor.qualification, doctor.specialization, doctor.contact_number, doctor.photo, doctor.biography or doctor.short_introduction]
    profile_completion = int(sum(1 for value in completion_fields if value) / len(completion_fields) * 100)
    salary_profile = getattr(staff_user, 'salary_profile', None)
    salary_payments = staff_user.salary_payments.all()[:6] if hasattr(staff_user, 'salary_payments') else []
    notifications = staff_user.notifications.filter(is_read=False)[:10] if hasattr(staff_user, 'notifications') else []
    return render(request, 'doctors/profile.html', {
        'form': form, 'doctor_profile': doctor, 'staff_user': staff_user,
        'profile_completion': profile_completion, 'salary_profile': salary_profile,
        'salary_payments': salary_payments, 'notifications': notifications,
    })


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
