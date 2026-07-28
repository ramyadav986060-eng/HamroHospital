from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User, AuditLog


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
