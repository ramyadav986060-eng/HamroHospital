from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User, AuditLog, Notification, HospitalSetting, StaffAttendance, StaffLeaveRequest, StaffSalaryProfile, StaffSalaryPayment


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    readonly_fields = ('staff_id', 'staff_barcode')
    list_display = ('staff_id', 'username', 'first_name', 'last_name', 'role', 'department', 'designation', 'is_department_head', 'is_active_staff', 'is_superuser')
    list_filter = ('role', 'department', 'is_department_head', 'is_active_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Role', {'fields': ('staff_id', 'staff_barcode', 'role', 'department', 'designation', 'employment_type', 'phone_number', 'is_department_head', 'is_active_staff')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Role', {'fields': ('role', 'department', 'designation', 'employment_type', 'phone_number', 'is_department_head', 'is_active_staff')}),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'role', 'user', 'is_read', 'created_at')
    list_filter = ('role', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(HospitalSetting)
class HospitalSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'emergency_contact', 'email', 'updated_display')
    fieldsets = (
        ('Basic Information', {'fields': ('name', 'logo', 'address', 'phone', 'emergency_contact', 'email', 'website')}),
        ('Registration / Finance', {'fields': ('pan_number', 'registration_number', 'default_currency', 'staff_discount_enabled', 'staff_discount_percent', 'required_daily_working_hours', 'default_weekend_days', 'paid_leave_days_per_month', 'paid_leave_days_per_year')}),
        ('Display / Printing', {'fields': ('opening_hours', 'footer_information', 'receipt_settings', 'print_settings', 'theme_color', 'default_timezone')}),
        ('Social Links', {'fields': ('facebook_url', 'twitter_url')}),
    )

    @admin.display(description='Updated')
    def updated_display(self, obj):
        return getattr(obj, 'id', '')

    def has_add_permission(self, request):
        return not HospitalSetting.objects.exists()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'user', 'description', 'patient_id_text', 'receipt_number', 'amount')
    list_filter = ('action', 'created_at')
    search_fields = ('description', 'patient_id_text', 'receipt_number', 'user__username')
    readonly_fields = [f.name for f in AuditLog._meta.fields]  # append-only: admin cannot edit values

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in', 'check_out', 'total_working_hours', 'status', 'source')
    list_filter = ('status', 'source', 'date')
    search_fields = ('staff__staff_id', 'staff__username', 'staff__first_name', 'staff__last_name', 'device_log_id')


@admin.register(StaffLeaveRequest)
class StaffLeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('staff__staff_id', 'staff__username', 'staff__first_name', 'staff__last_name', 'reason')
    readonly_fields = ('created_at', 'reviewed_at')


@admin.register(StaffSalaryProfile)
class StaffSalaryProfileAdmin(admin.ModelAdmin):
    list_display = ('staff', 'bank_name', 'bank_account_number', 'base_monthly_salary', 'per_day_salary', 'bonus_amount', 'is_active')
    list_filter = ('is_active', 'bank_name')
    search_fields = ('staff__staff_id', 'staff__username', 'staff__first_name', 'staff__last_name', 'bank_account_number')


@admin.register(StaffSalaryPayment)
class StaffSalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('staff', 'year', 'month', 'present_days', 'leave_days', 'half_days', 'absent_days', 'net_amount', 'status')
    list_filter = ('year', 'month', 'status')
    search_fields = ('staff__staff_id', 'staff__username', 'staff__first_name', 'staff__last_name')
    readonly_fields = ('created_at',)

