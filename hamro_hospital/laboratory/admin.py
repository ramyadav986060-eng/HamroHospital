from django.contrib import admin
from laboratory.models import LabTest, LabPanel, LabParameter, LabResultValue


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'sample_type', 'price', 'is_active')
    list_filter = ('department', 'sample_type', 'is_active')
    search_fields = ('name',)


class LabParameterInline(admin.TabularInline):
    model = LabParameter
    extra = 1


@admin.register(LabPanel)
class LabPanelAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [LabParameterInline]


@admin.register(LabParameter)
class LabParameterAdmin(admin.ModelAdmin):
    list_display = ('panel', 'name', 'unit', 'normal_range', 'display_order')
    list_filter = ('panel',)
    search_fields = ('name', 'panel__name')


@admin.register(LabResultValue)
class LabResultValueAdmin(admin.ModelAdmin):
    list_display = ('lab_request', 'parameter', 'value', 'flag')
    list_filter = ('flag', 'parameter__panel')
    search_fields = ('lab_request__lab_code', 'parameter__name', 'value')
