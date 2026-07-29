from django.contrib import admin, messages
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from accounts.models import User, Role
from doctors.models import Doctor, DoctorLeave, DoctorWeeklyQuota, DoctorQuotaOverride, DoctorSchedule


class DoctorScheduleInline(admin.TabularInline):
    """Sunday-Saturday OPD schedule shown on public department/doctor pages."""
    model = DoctorSchedule
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'department', 'unit', 'specialization', 'consultation_fee', 'user_account', 'is_active', 'is_featured')
    list_filter = ('department', 'unit', 'is_active', 'is_featured')
    search_fields = ('full_name', 'specialization', 'qualification', 'user_account__username')
    autocomplete_fields = ('unit', 'user_account')
    inlines = [DoctorScheduleInline]

    def _unique_username(self, full_name):
        base = slugify(full_name).replace('-', '.') or 'doctor'
        username = base
        i = 1
        while User.objects.filter(username__iexact=username).exists():
            i += 1
            username = f'{base}{i}'
        return username

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.user_account_id:
            username = self._unique_username(obj.full_name)
            password = f'Dr@{get_random_string(8)}'
            parts = obj.full_name.strip().split(' ', 1)
            user = User.objects.create(
                username=username,
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else '',
                role=Role.DOCTOR,
                is_staff=True,
                is_active=True,
                is_active_staff=True,
                phone_number=obj.contact_number,
            )
            user.set_password(password)
            user.save(update_fields=['password'])
            obj.user_account = user
            obj.save(update_fields=['user_account'])
            messages.success(request, f'Doctor login account created: {username} / {password}')
        else:
            user = obj.user_account
            changed = False
            if user.role != Role.DOCTOR:
                user.role = Role.DOCTOR
                changed = True
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if changed:
                user.save()


@admin.register(DoctorWeeklyQuota)
class DoctorWeeklyQuotaAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'weekday', 'quota')
    list_filter = ('weekday', 'doctor__department')
    search_fields = ('doctor__full_name',)
    autocomplete_fields = ('doctor',)


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'reason')
    list_filter = ('date', 'doctor__department')
    search_fields = ('doctor__full_name', 'reason')
    autocomplete_fields = ('doctor',)
    date_hierarchy = 'date'


@admin.register(DoctorQuotaOverride)
class DoctorQuotaOverrideAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'quota', 'created_by', 'created_at')
    list_filter = ('date', 'doctor__department')
    search_fields = ('doctor__full_name',)
    autocomplete_fields = ('doctor',)
    readonly_fields = ('created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
