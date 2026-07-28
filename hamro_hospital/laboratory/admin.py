from django.contrib import admin
from laboratory.models import LabTest


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'sample_type', 'price', 'is_active')
    list_filter = ('department', 'sample_type', 'is_active')
    search_fields = ('name',)
