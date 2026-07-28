from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User, AuditLog, Notification, HospitalSetting


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_active_staff', 'is_superuser')
    list_filter = ('role', 'is_active_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Role', {'fields': ('role', 'phone_number', 'is_active_staff')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Role', {'fields': ('role', 'phone_number', 'is_active_staff')}),
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
        ('Registration / Finance', {'fields': ('pan_number', 'registration_number', 'default_currency')}),
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
