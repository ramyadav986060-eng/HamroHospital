from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required, doctor_required
from doctors.models import Doctor
from doctors.forms import DoctorForm


@super_admin_required
def doctor_list(request):
    doctors = Doctor.objects.select_related('department').all()
    return render(request, 'doctors/doctor_list.html', {'doctors': doctors})


@super_admin_required
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save()
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
        messages.success(request, f'Dr. {name} has been deactivated (kept for historical visit records).')
        return redirect('doctors:doctor_list')
    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})


@doctor_required
def doctor_dashboard(request):
    """
    Doctor's own landing dashboard. The full consultation queue is built in
    the `consultations` app (next checkpoint); this page already gives the
    doctor their profile snapshot and today's OPD visit count.
    """
    from patients.models import Visit
    import datetime

    doctor_profile = getattr(request.user, 'doctor_profile', None)
    todays_visits = 0
    if doctor_profile:
        todays_visits = Visit.objects.filter(doctor=doctor_profile, visit_date=datetime.date.today()).count()

    return render(request, 'doctors/dashboard.html', {
        'doctor_profile': doctor_profile,
        'todays_visits': todays_visits,
    })
