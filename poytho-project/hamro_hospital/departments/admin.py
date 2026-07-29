from django.contrib import admin
from departments.models import Department, DepartmentUnit


class DepartmentUnitInline(admin.TabularInline):
    model = DepartmentUnit
    extra = 1


@admin.register(DepartmentUnit)
class DepartmentUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'display_order')
    list_filter = ('department',)
    search_fields = ('name', 'department__name')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'consultation_fee', 'active_doctor_count', 'is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DepartmentUnitInline]
