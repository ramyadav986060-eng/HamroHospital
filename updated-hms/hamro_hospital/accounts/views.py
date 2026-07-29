from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse

from accounts.decorators import super_admin_required, role_required
from accounts.forms import StyledAuthenticationForm, StaffCreateForm, StaffEditForm
from accounts.models import User, AuditLog, Role, HospitalSetting
from accounts.utils import write_audit_log
from reports.excel_utils import export_rows_to_excel, export_rows_to_pdf


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


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD)
def staff_list(request):
    staff = User.objects.all().select_related('department').order_by('role', 'first_name')
    if request.user.effective_role == Role.DEPARTMENT_HEAD and not request.user.is_superuser:
        staff = staff.filter(department=request.user.department)
    return render(request, 'accounts/staff_list.html', {'staff': staff, 'roles': Role.choices})


@super_admin_required
def staff_create(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == Role.DOCTOR and not hasattr(user, 'doctor_profile'):
                from departments.models import Department
                from doctors.models import Doctor
                department = user.department or Department.objects.filter(is_active=True).first()
                if department:
                    full_name = user.get_full_name() or user.username
                    Doctor.objects.create(
                        user_account=user, department=department, full_name=full_name,
                        qualification='Not specified', specialization=user.designation or 'General',
                        consultation_fee=0, contact_number=user.phone_number, is_active=True,
                    )
            write_audit_log(request, AuditLog.Action.USER_CREATED,
                             f"Created staff account {user.username} ({user.get_role_display()})")
            messages.success(request, f'Staff account "{user.username}" created successfully.')
            return redirect('accounts:staff_list')
    else:
        form = StaffCreateForm()
    return render(request, 'accounts/staff_form.html', {'form': form, 'title': 'Add Staff Member'})


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT, Role.DEPARTMENT_HEAD)
def staff_edit(request, pk):
    staff_member = get_object_or_404(User, pk=pk)
    if request.user.effective_role == Role.DEPARTMENT_HEAD and not request.user.is_superuser:
        if not request.user.department_id or staff_member.department_id != request.user.department_id:
            messages.error(request, 'Department Heads can only manage staff in their own department.')
            return redirect('accounts:staff_list')
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
    """Super Admin backup center: database, media, full backup, restore guidance and history."""
    import os
    from django.conf import settings

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    backups = []
    if os.path.isdir(backup_dir):
        for name in sorted(os.listdir(backup_dir), reverse=True):
            if name.endswith(('.json', '.zip')):
                full_path = os.path.join(backup_dir, name)
                backups.append({
                    'name': name,
                    'size_kb': round(os.path.getsize(full_path) / 1024, 1),
                    'modified': os.path.getmtime(full_path),
                    'kind': 'Database' if name.endswith('.json') else ('Full / Media' if 'full' in name else 'Media'),
                })
    return render(request, 'accounts/backup_list.html', {
        'backups': backups,
        'schedule_command': 'python manage.py backup_full',
        'cloud_note': 'Configure S3, Google Drive, NAS, or another provider during deployment and sync BASE_DIR/backups securely.',
    })


@super_admin_required
def backup_create(request):
    if request.method == 'POST':
        from django.core import management
        backup_type = request.POST.get('backup_type', 'database')
        if backup_type == 'media':
            management.call_command('backup_media')
            label = 'media backup'
        elif backup_type == 'full':
            management.call_command('backup_full')
            label = 'full database + media backup'
        else:
            management.call_command('backup_data')
            label = 'database backup'
        write_audit_log(request, AuditLog.Action.BACKUP_CREATED, f'System {label} created via dashboard')
        messages.success(request, f'{label.title()} created successfully.')
    return redirect('accounts:backup_list')


@super_admin_required
def backup_download(request, name):
    import os
    from django.conf import settings
    from django.http import FileResponse, Http404
    safe_name = os.path.basename(name)
    path = os.path.join(settings.BASE_DIR, 'backups', safe_name)
    if not os.path.exists(path) or not safe_name.endswith(('.json', '.zip')):
        raise Http404('Backup not found')
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=safe_name)


@super_admin_required
def backup_restore(request):
    if request.method == 'POST':
        import os
        from django.conf import settings
        from django.core import management
        backup_name = os.path.basename(request.POST.get('backup_name', ''))
        confirmation = request.POST.get('confirmation', '')
        path = os.path.join(settings.BASE_DIR, 'backups', backup_name)
        if confirmation != 'RESTORE':
            messages.error(request, 'Type RESTORE to confirm this destructive operation.')
        elif not backup_name.endswith('.json') or not os.path.exists(path):
            messages.error(request, 'Only database .json backups can be restored from the web dashboard. Full/media ZIP restore must be performed on the server after verification.')
        else:
            management.call_command('restore_data', path, yes=True)
            write_audit_log(request, AuditLog.Action.RESTORE_PERFORMED, f'Database restored from {backup_name}')
            messages.success(request, f'Database restore completed from {backup_name}.')
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
    q = request.GET.get('q', '').strip()
    department_id = request.GET.get('department', '').strip()
    date_filter = request.GET.get('date', '')
    month = request.GET.get('month', '')
    year = request.GET.get('year', '')
    start = request.GET.get('start_date', '')
    end = request.GET.get('end_date', '')
    if q:
        records = records.filter(
            Q(staff__staff_id__icontains=q) | Q(staff__username__icontains=q) |
            Q(staff__first_name__icontains=q) | Q(staff__last_name__icontains=q) |
            Q(staff__phone_number__icontains=q)
        )
    if department_id:
        records = records.filter(staff__department_id=department_id)

    # Build a compact Nepali-calendar-style month grid using the selected
    # month/year. Dates remain stored as AD for database safety; the grid is
    # display-only and ready to connect to a BS converter later.
    today = datetime.date.today()
    cal_year = int(year) if str(year).isdigit() else today.year
    cal_month = int(month) if str(month).isdigit() else today.month
    import calendar
    month_start = datetime.date(cal_year, cal_month, 1)
    _, month_days_count = calendar.monthrange(cal_year, cal_month)
    month_end = datetime.date(cal_year, cal_month, month_days_count)
    calendar_records = list(records.filter(date__range=[month_start, month_end]).select_related('staff'))
    by_date = {}
    for rec in calendar_records:
        by_date.setdefault(rec.date, []).append(rec)
    weekend_codes = [c.strip().lower() for c in HospitalSetting.get_solo().default_weekend_days.split(',') if c.strip()]
    weekday_code = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    calendar_days = []
    for day in range(1, month_days_count + 1):
        date_obj = datetime.date(cal_year, cal_month, day)
        recs = by_date.get(date_obj, [])
        counts = {'present': 0, 'leave': 0, 'absent': 0, 'partial': 0, 'holiday': 0}
        for rec in recs:
            counts[rec.status] = counts.get(rec.status, 0) + 1
        is_weekend = weekday_code[date_obj.weekday()] in weekend_codes
        display_status = 'holiday' if is_weekend and not recs else ('present' if counts.get('present') else 'leave' if counts.get('leave') else 'absent' if counts.get('absent') else 'partial' if counts.get('partial') else 'blank')
        calendar_days.append({'date': date_obj, 'day': day, 'records': recs, 'counts': counts, 'is_weekend': is_weekend, 'display_status': display_status})

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
    if request.GET.get('export') in ['excel', 'pdf']:
        headers = ['Date', 'Staff ID', 'Name', 'Department', 'Check In', 'Check Out', 'Hours', 'Status']
        rows = [(a.date, a.staff.staff_id, a.staff.get_full_name() or a.staff.username, a.staff.department.name if a.staff.department else '', a.check_in, a.check_out, a.total_working_hours, a.get_status_display()) for a in records[:5000]]
        if request.GET.get('export') == 'pdf':
            return export_rows_to_pdf(headers, rows, 'staff_attendance.pdf', 'Staff Attendance Report')
        return export_rows_to_excel(headers, rows, 'staff_attendance.xlsx', 'Attendance')
    page_obj = Paginator(records, 31).get_page(request.GET.get('page'))
    from departments.models import Department
    return render(request, 'accounts/staff_attendance.html', {
        'page_obj': page_obj, 'filters': request.GET, 'departments': Department.objects.filter(is_active=True),
        'calendar_days': calendar_days, 'calendar_year': cal_year, 'calendar_month': cal_month,
    })


@login_required
def staff_leave_request(request):
    from accounts.forms import StaffLeaveRequestForm
    from accounts.utils import create_notification
    if request.method == 'POST':
        form = StaffLeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.staff = request.user
            if leave.exceeds_paid_leave_limit():
                leave.requires_super_admin_override = True
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
                if leave.requires_super_admin_override and not (request.user.is_superuser or request.user.effective_role == Role.SUPER_ADMIN):
                    messages.error(request, 'This leave exceeds the monthly paid leave limit and requires Main Super Admin approval.')
                    return redirect('accounts:staff_leave_review', pk=leave.pk)
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

@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def staff_salary_profiles(request):
    from accounts.models import StaffSalaryProfile
    for staff in User.objects.filter(is_active_staff=True):
        StaffSalaryProfile.objects.get_or_create(staff=staff)
    profiles = StaffSalaryProfile.objects.select_related('staff', 'staff__department').all()
    return render(request, 'accounts/staff_salary_profiles.html', {'profiles': profiles})


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
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


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
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


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
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


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def staff_salary_slip(request, pk):
    from accounts.models import StaffSalaryPayment
    payment = get_object_or_404(StaffSalaryPayment.objects.select_related('staff', 'staff__department', 'prepared_by'), pk=pk)
    return render(request, 'accounts/staff_salary_slip.html', {'payment': payment})


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def staff_salary_mark_paid(request, pk):
    from django.utils import timezone
    from accounts.models import StaffSalaryPayment
    payment = get_object_or_404(StaffSalaryPayment, pk=pk)
    if request.method == 'POST':
        payment.status = StaffSalaryPayment.Status.PAID
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at'])
        messages.success(request, 'Salary marked as paid.')
    return redirect('accounts:staff_salary_payments')


@role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)
def staff_salary_export(request):
    from accounts.models import StaffSalaryPayment
    payments = StaffSalaryPayment.objects.select_related('staff', 'staff__department').all()
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year:
        payments = payments.filter(year=year)
    if month:
        payments = payments.filter(month=month)
    headers = ['Staff ID', 'Name', 'Department', 'Year', 'Month', 'Present', 'Leave', 'Absent', 'Base', 'Bonus', 'Deductions', 'Net', 'Status']
    rows = [(p.staff.staff_id, p.staff.get_full_name() or p.staff.username, p.staff.department.name if p.staff.department else '', p.year, p.month, p.present_days, p.leave_days, p.absent_days, p.base_amount, p.bonus_amount, p.deductions, p.net_amount, p.get_status_display()) for p in payments[:5000]]
    if request.GET.get('export') == 'pdf':
        return export_rows_to_pdf(headers, rows, 'salary_report.pdf', 'Salary / Payroll Report')
    return export_rows_to_excel(headers, rows, 'salary_report.xlsx', 'Salary')


@login_required
def staff_attendance_punch(request):
    from django.utils import timezone
    from accounts.models import StaffAttendance
    if request.method == 'POST':
        staff_id = (request.POST.get('staff_id') or '').strip()
        direction = (request.POST.get('direction') or 'in').strip().lower()
        staff = User.objects.filter(staff_id__iexact=staff_id, is_active_staff=True).first()
        if not staff:
            messages.error(request, 'No active staff found for that Staff ID / barcode.')
            return redirect('accounts:staff_attendance_punch')
        now = timezone.now()
        att, _ = StaffAttendance.objects.get_or_create(staff=staff, date=now.date(), defaults={'source': 'manual_punch'})
        if direction == 'out':
            att.check_out = now
        else:
            att.check_in = now
        att.source = 'manual_punch'
        att.save()
        messages.success(request, f'{staff.get_full_name() or staff.username} marked {direction.upper()} at {now:%H:%M}. Status: {att.get_status_display()}')
        return redirect('accounts:staff_attendance')
    return render(request, 'accounts/staff_attendance_punch.html')


def staff_attendance_device_punch(request):
    import datetime
    from django.conf import settings
    from django.http import JsonResponse
    from django.utils import timezone
    from accounts.models import StaffAttendance
    expected_key = getattr(settings, 'FINGERPRINT_DEVICE_API_KEY', '')
    if expected_key and request.GET.get('api_key') != expected_key and request.POST.get('api_key') != expected_key:
        return JsonResponse({'ok': False, 'error': 'Invalid device API key.'}, status=403)
    data = request.POST if request.method == 'POST' else request.GET
    staff_id = (data.get('staff_id') or '').strip()
    direction = (data.get('direction') or '').strip().lower()
    timestamp = (data.get('timestamp') or '').strip()
    device_log_id = (data.get('device_log_id') or '').strip()
    if not staff_id:
        return JsonResponse({'ok': False, 'error': 'staff_id is required.'}, status=400)
    staff = User.objects.filter(staff_id__iexact=staff_id, is_active_staff=True).first()
    if not staff:
        return JsonResponse({'ok': False, 'error': 'Staff not found.', 'type': 'unknown'}, status=404)
    if timestamp:
        try:
            punch_time = datetime.datetime.fromisoformat(timestamp)
            if timezone.is_naive(punch_time):
                punch_time = timezone.make_aware(punch_time)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Invalid timestamp.'}, status=400)
    else:
        punch_time = timezone.now()
    att, _ = StaffAttendance.objects.get_or_create(staff=staff, date=punch_time.date(), defaults={'source': 'fingerprint'})
    if direction == 'out':
        att.check_out = punch_time
    elif direction == 'in':
        att.check_in = punch_time
    else:
        if not att.check_in or punch_time < att.check_in:
            att.check_in = punch_time
        if not att.check_out or punch_time > att.check_out:
            att.check_out = punch_time
    att.source = 'fingerprint'
    if device_log_id:
        att.device_log_id = device_log_id
    att.save()
    return JsonResponse({'ok': True, 'type': 'staff', 'label': 'STAFF', 'staff_id': staff.staff_id, 'staff_name': staff.get_full_name() or staff.username, 'date': att.date.isoformat(), 'check_in': att.check_in.isoformat() if att.check_in else '', 'check_out': att.check_out.isoformat() if att.check_out else '', 'hours': str(att.total_working_hours), 'status': att.get_status_display()})


@super_admin_required
def system_readiness(request):
    from django.conf import settings
    checks = [
        {'name': 'Django DEBUG disabled for production', 'ok': not settings.DEBUG, 'detail': f'DEBUG={settings.DEBUG}'},
        {'name': 'Redis URL configured', 'ok': bool(getattr(settings, 'REDIS_URL', '')), 'detail': getattr(settings, 'REDIS_URL', '') or 'Using local in-memory fallback'},
        {'name': 'Celery broker configured', 'ok': bool(getattr(settings, 'CELERY_BROKER_URL', '')), 'detail': getattr(settings, 'CELERY_BROKER_URL', '')},
        {'name': 'eSewa merchant configured', 'ok': bool(settings.ESEWA_MERCHANT_CODE and settings.ESEWA_SECRET_KEY), 'detail': f"sandbox={settings.ESEWA_SANDBOX}, merchant={settings.ESEWA_MERCHANT_CODE}"},
        {'name': 'Fingerprint endpoint available', 'ok': True, 'detail': request.build_absolute_uri(reverse('accounts:staff_attendance_device_punch'))},
        {'name': 'Staff discount configured', 'ok': True, 'detail': f"enabled={HospitalSetting.get_solo().staff_discount_enabled}, percent={HospitalSetting.get_solo().staff_discount_percent}%"},
    ]
    return render(request, 'accounts/system_readiness.html', {'checks': checks})

@login_required
def staff_change_password(request):
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:staff_profile')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    return render(request, 'accounts/staff_change_password.html', {'form': form})
