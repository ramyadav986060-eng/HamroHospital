from django.contrib import admin
from doctors.models import Doctor, DoctorLeave, DoctorWeeklyQuota, DoctorQuotaOverride, DoctorSchedule


class DoctorScheduleInline(admin.TabularInline):
    """Sunday-Saturday OPD schedule shown on the public department/doctor pages."""
    model = DoctorSchedule
    extra = 1


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'department', 'unit', 'specialization', 'consultation_fee', 'is_active', 'is_featured')
    list_filter = ('department', 'unit', 'is_active', 'is_featured')
    search_fields = ('full_name', 'specialization', 'qualification')
    autocomplete_fields = ('unit',)
    inlines = [DoctorScheduleInline]


@admin.register(DoctorWeeklyQuota)
class DoctorWeeklyQuotaAdmin(admin.ModelAdmin):
    """Super Admin sets each doctor's default patients-per-day, per weekday (spec section 12)."""
    list_display = ('doctor', 'weekday', 'quota')
    list_filter = ('weekday', 'doctor__department')
    search_fields = ('doctor__full_name',)
    autocomplete_fields = ('doctor',)


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    """Super Admin (or the doctor's department) marks leave/holiday/off-duty days."""
    list_display = ('doctor', 'date', 'reason')
    list_filter = ('date', 'doctor__department')
    search_fields = ('doctor__full_name', 'reason')
    autocomplete_fields = ('doctor',)
    date_hierarchy = 'date'


@admin.register(DoctorQuotaOverride)
class DoctorQuotaOverrideAdmin(admin.ModelAdmin):
    """Super Admin override of a doctor's quota for one specific date."""
    list_display = ('doctor', 'date', 'quota', 'created_by', 'created_at')
    list_filter = ('date', 'doctor__department')
    search_fields = ('doctor__full_name',)
    autocomplete_fields = ('doctor',)
    readonly_fields = ('created_by', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
