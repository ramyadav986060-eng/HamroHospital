from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse

from accounts.decorators import super_admin_required
from accounts.forms import StyledAuthenticationForm, StaffCreateForm, StaffEditForm
from accounts.models import User, AuditLog, Role
from accounts.utils import write_audit_log


class StaffLoginView(LoginView):
    """Single login screen for all staff roles; redirect target depends on role."""
    template_name = 'accounts/login.html'
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        write_audit_log(self.request, AuditLog.Action.LOGIN,
                         f"{self.request.user.username} logged in")
        return response


@login_required
def logout_view(request):
    write_audit_log(request, AuditLog.Action.LOGOUT, f"{request.user.username} logged out")
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('website:home')


@login_required
def post_login_redirect(request):
    """Send every freshly-logged-in user straight to their own role dashboard."""
    return redirect(request.user.dashboard_url_name())


@super_admin_required
def dashboard_super_admin(request):
    from departments.models import Department
    from doctors.models import Doctor
    from patients.models import Patient, Visit

    context = {
        'total_departments': Department.objects.count(),
        'total_doctors': Doctor.objects.filter(is_active=True).count(),
        'total_patients': Patient.objects.count(),
        'total_visits_today': Visit.objects.filter(visit_date=__import__('datetime').date.today()).count(),
        'total_staff': User.objects.filter(is_active_staff=True).count(),
        'recent_audit_logs': AuditLog.objects.select_related('user')[:15],
    }
    return render(request, 'accounts/dashboard_super_admin.html', context)


@super_admin_required
def staff_list(request):
    staff = User.objects.all().order_by('role', 'first_name')
    return render(request, 'accounts/staff_list.html', {'staff': staff, 'roles': Role.choices})


@super_admin_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            write_audit_log(request, AuditLog.Action.USER_CREATED,
                             f"Created staff account {user.username} ({user.get_role_display()})")
            messages.success(request, f'Staff account "{user.username}" created successfully.')
            return redirect('accounts:staff_list')
    else:
        form = StaffCreateForm()
    return render(request, 'accounts/staff_form.html', {'form': form, 'title': 'Add Staff Member'})


@super_admin_required
def staff_edit(request, pk):
    staff_member = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=staff_member)
        if form.is_valid():
            was_active = staff_member.is_active_staff
            form.save()
            if was_active and not staff_member.is_active_staff:
                write_audit_log(request, AuditLog.Action.USER_DEACTIVATED,
                                 f"Deactivated staff account {staff_member.username}")
            messages.success(request, f'Staff account "{staff_member.username}" updated.')
            return redirect('accounts:staff_list')
    else:
        form = StaffEditForm(instance=staff_member)
    return render(request, 'accounts/staff_form.html', {
        'form': form, 'title': f'Edit {staff_member.username}', 'staff_member': staff_member,
    })


@super_admin_required
def audit_log_list(request):
    import datetime
    from django.utils import timezone
    from django.db.models import Q

    logs = AuditLog.objects.select_related('user').all()

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    seven_days_ago = today - datetime.timedelta(days=7)
    current_year = today.year

    date_filter = request.GET.get('date_filter', 'current_year')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    if date_filter == 'today':
        logs = logs.filter(created_at__date=today)
    elif date_filter == 'yesterday':
        logs = logs.filter(created_at__date=yesterday)
    elif date_filter == '7_days':
        logs = logs.filter(created_at__date__gte=seven_days_ago)
    elif date_filter == 'custom_date' and start_date_str:
        try:
            start_date = datetime.date.fromisoformat(start_date_str)
            logs = logs.filter(created_at__date=start_date)
        except ValueError:
            pass
    elif date_filter == 'custom_range' and start_date_str:
        try:
            start_date = datetime.date.fromisoformat(start_date_str)
            if end_date_str:
                end_date = datetime.date.fromisoformat(end_date_str)
                logs = logs.filter(created_at__date__range=[start_date, end_date])
            else:
                logs = logs.filter(created_at__date__gte=start_date)
        except ValueError:
            pass
    elif date_filter == 'current_year' or not date_filter:
        logs = logs.filter(created_at__year=current_year)

    action = request.GET.get('action', '')
    if action:
        logs = logs.filter(action=action)

    q = request.GET.get('q', '').strip()
    if q:
        logs = logs.filter(
            Q(patient_id_text__icontains=q) |
            Q(receipt_number__icontains=q) |
            Q(description__icontains=q)
        )

    logs = logs[:500]  # keep the page light and fast
    return render(request, 'accounts/audit_log_list.html', {
        'logs': logs,
        'actions': AuditLog.Action.choices,
        'selected_action': action,
        'date_filter': date_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'q': q,
    })


@super_admin_required
def backup_list(request):
    """
    Backup & restore (spec section 11). Lists existing backups and lets
    Super Admin trigger a new one; restoring is intentionally left to the
    command line (``python manage.py restore_data <file>``) since it is a
    destructive, whole-database operation that should never be one click.
    """
    import os
    from django.conf import settings

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []
    if os.path.isdir(backup_dir):
        for name in sorted(os.listdir(backup_dir), reverse=True):
            if name.endswith('.json'):
                full_path = os.path.join(backup_dir, name)
                backups.append({
                    'name': name,
                    'size_kb': round(os.path.getsize(full_path) / 1024, 1),
                })
    return render(request, 'accounts/backup_list.html', {'backups': backups})


@super_admin_required
def backup_create(request):
    if request.method == 'POST':
        from django.core import management
        management.call_command('backup_data')
        write_audit_log(request, AuditLog.Action.BACKUP_CREATED, 'System backup created via dashboard')
        messages.success(request, 'Backup created successfully.')
    return redirect('accounts:backup_list')


@super_admin_required
def notification_create(request):
    from accounts.forms import NotificationForm
    from accounts.utils import write_audit_log
    from accounts.models import AuditLog

    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save()
            write_audit_log(request, AuditLog.Action.OTHER, f"Created notification: {notification.title}")
            messages.success(request, 'Notification created successfully.')
            return redirect('accounts:dashboard_super_admin')
    else:
        form = NotificationForm()
    return render(request, 'accounts/notification_form.html', {'form': form, 'title': 'Create System Notification'})

@login_required
def mark_all_read(request):
    """Mark all unread notifications of the logged in user as read."""
    from accounts.models import Notification
    from django.db.models import Q
    Notification.objects.filter(is_read=False).filter(
        Q(user=request.user) | Q(role=request.user.role)
    ).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect(request.user.dashboard_url_name())


@super_admin_required
def hospital_settings_view(request):
    """
    Allow Super Admin to view and update the Hospital Settings (spec section 6).
    """
    from accounts.models import HospitalSetting
    from accounts.forms import HospitalSettingForm

    setting = HospitalSetting.get_solo()

    if request.method == 'POST':
        form = HospitalSettingForm(request.POST, request.FILES, instance=setting)
        if form.is_valid():
            form.save()
            write_audit_log(
                request, AuditLog.Action.OTHER,
                f"Updated hospital settings for: {setting.name}"
            )
            messages.success(request, 'Hospital Settings updated successfully.')
            return redirect('accounts:hospital_settings')
    else:
        form = HospitalSettingForm(instance=setting)

    return render(request, 'accounts/hospital_settings.html', {
        'form': form,
        'setting': setting,
    })


@login_required
def staff_profile(request):
    return render(request, 'accounts/staff_profile.html', {'staff': request.user})


@super_admin_required
def staff_card(request, pk):
    staff = get_object_or_404(User, pk=pk)
    return render(request, 'accounts/staff_card.html', {'staff': staff})


@login_required
def staff_attendance(request):
    import datetime
    from django.core.paginator import Paginator
    from accounts.models import StaffAttendance
    records = StaffAttendance.objects.select_related('staff')
    if not (request.user.is_superuser or request.user.effective_role in [Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT]):
        if request.user.is_department_head and request.user.department_id:
            records = records.filter(staff__department=request.user.department)
        else:
            records = records.filter(staff=request.user)
    date_filter = request.GET.get('date', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')
    start = request.GET.get('start_date', '')
    end = request.GET.get('end_date', '')
    if date_filter:
        records = records.filter(date=date_filter)
    if month and year:
        records = records.filter(date__month=month, date__year=year)
    elif year:
        records = records.filter(date__year=year)
    if start:
        records = records.filter(date__gte=start)
    if end:
        records = records.filter(date__lte=end)
    page_obj = Paginator(records, 31).get_page(request.GET.get('page'))
    return render(request, 'accounts/staff_attendance.html', {'page_obj': page_obj, 'filters': request.GET})


@login_required
def staff_leave_request(request):
    from accounts.forms import StaffLeaveRequestForm
    from accounts.utils import create_notification
    if request.method == 'POST':
        form = StaffLeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.staff = request.user
            leave.save()
            if request.user.department_id:
                heads = User.objects.filter(department=request.user.department, is_department_head=True, is_active_staff=True)
                for head in heads:
                    create_notification('Leave Request', f'{request.user.get_full_name() or request.user.username} requested leave.', user=head, related_url=reverse('accounts:staff_leave_review', args=[leave.pk]))
            create_notification('Leave Request', f'{request.user.get_full_name() or request.user.username} requested leave.', role=Role.SUPER_ADMIN, related_url=reverse('accounts:staff_leave_review', args=[leave.pk]))
            messages.success(request, 'Leave request submitted.')
            return redirect('accounts:staff_leave_list')
    else:
        form = StaffLeaveRequestForm()
    return render(request, 'accounts/staff_leave_form.html', {'form': form})


@login_required
def staff_leave_list(request):
    from accounts.models import StaffLeaveRequest
    leaves = StaffLeaveRequest.objects.select_related('staff', 'reviewed_by')
    if not (request.user.is_superuser or request.user.effective_role == Role.SUPER_ADMIN):
        if request.user.is_department_head and request.user.department_id:
            leaves = leaves.filter(staff__department=request.user.department)
        else:
            leaves = leaves.filter(staff=request.user)
    return render(request, 'accounts/staff_leave_list.html', {'leaves': leaves})


@login_required
def staff_leave_review(request, pk):
    from accounts.forms import StaffLeaveReviewForm
    from accounts.models import StaffLeaveRequest
    leave = get_object_or_404(StaffLeaveRequest.objects.select_related('staff'), pk=pk)
    allowed = request.user.is_superuser or request.user.effective_role == Role.SUPER_ADMIN or (request.user.is_department_head and request.user.department_id == leave.staff.department_id)
    if not allowed:
        messages.error(request, "You don't have permission to review this leave request.")
        return redirect('accounts:staff_leave_list')
    if request.method == 'POST':
        form = StaffLeaveReviewForm(request.POST, instance=leave)
        if form.is_valid():
            status = form.cleaned_data['status']
            notes = form.cleaned_data.get('review_notes', '')
            if status == StaffLeaveRequest.Status.APPROVED:
                leave.approve(request.user, notes)
            elif status == StaffLeaveRequest.Status.REJECTED:
                leave.reject(request.user, notes)
            else:
                form.save()
            messages.success(request, 'Leave request updated.')
            return redirect('accounts:staff_leave_list')
    else:
        form = StaffLeaveReviewForm(instance=leave)
    return render(request, 'accounts/staff_leave_review.html', {'form': form, 'leave': leave})


@login_required
def staff_lookup_api(request):
    from django.http import JsonResponse
    code = (request.GET.get('code') or request.GET.get('q') or '').strip()
    if not code:
        return JsonResponse({'found': False, 'error': 'No code supplied.'}, status=400)
    staff = User.objects.filter(staff_id__iexact=code).select_related('department').first()
    if not staff:
        staff = User.objects.filter(username__iexact=code).select_related('department').first()
    if not staff:
        return JsonResponse({'found': False, 'type': 'unknown', 'error': 'No staff matches that code.'})
    return JsonResponse({
        'found': True,
        'type': 'staff',
        'label': 'STAFF',
        'id': staff.id,
        'staff_id': staff.staff_id,
        'full_name': staff.get_full_name() or staff.username,
        'role': staff.get_role_display(),
        'department': staff.department.name if staff.department else '',
        'designation': staff.designation,
        'barcode_url': staff.staff_barcode.url if staff.staff_barcode else '',
    })

@super_admin_required
def staff_salary_profiles(request):
    from accounts.models import StaffSalaryProfile
    for staff in User.objects.filter(is_active_staff=True):
        StaffSalaryProfile.objects.get_or_create(staff=staff)
    profiles = StaffSalaryProfile.objects.select_related('staff', 'staff__department').all()
    return render(request, 'accounts/staff_salary_profiles.html', {'profiles': profiles})


@super_admin_required
def staff_salary_profile_edit(request, staff_id):
    from accounts.forms import StaffSalaryProfileForm
    from accounts.models import StaffSalaryProfile
    staff = get_object_or_404(User, pk=staff_id)
    profile, _ = StaffSalaryProfile.objects.get_or_create(staff=staff)
    if request.method == 'POST':
        form = StaffSalaryProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary profile saved.')
            return redirect('accounts:staff_salary_profiles')
    else:
        form = StaffSalaryProfileForm(instance=profile)
    return render(request, 'accounts/staff_salary_profile_form.html', {'form': form, 'staff_member': staff})


@super_admin_required
def staff_salary_generate(request):
    import calendar
    from django.utils import timezone
    from accounts.models import StaffAttendance, StaffSalaryPayment
    year = int(request.POST.get('year') or request.GET.get('year') or timezone.now().year)
    month = int(request.POST.get('month') or request.GET.get('month') or timezone.now().month)
    if request.method == 'POST':
        _, days_in_month = calendar.monthrange(year, month)
        count = 0
        for staff in User.objects.filter(is_active_staff=True).select_related('salary_profile'):
            records = StaffAttendance.objects.filter(staff=staff, date__year=year, date__month=month)
            payment, _ = StaffSalaryPayment.objects.get_or_create(staff=staff, year=year, month=month, defaults={'prepared_by': request.user})
            payment.working_days = days_in_month
            payment.present_days = records.filter(status=StaffAttendance.Status.PRESENT).count()
            payment.leave_days = records.filter(status=StaffAttendance.Status.LEAVE).count()
            payment.absent_days = max(0, days_in_month - payment.present_days - payment.leave_days)
            payment.prepared_by = request.user
            payment.calculate()
            payment.save()
            count += 1
        messages.success(request, f'Salary generated for {count} staff for {year}-{month:02d}.')
        return redirect('accounts:staff_salary_payments')
    return render(request, 'accounts/staff_salary_generate.html', {'year': year, 'month': month})


@super_admin_required
def staff_salary_payments(request):
    from accounts.models import StaffSalaryPayment
    payments = StaffSalaryPayment.objects.select_related('staff', 'prepared_by').all()
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year:
        payments = payments.filter(year=year)
    if month:
        payments = payments.filter(month=month)
    return render(request, 'accounts/staff_salary_payments.html', {'payments': payments, 'year': year or '', 'month': month or ''})
