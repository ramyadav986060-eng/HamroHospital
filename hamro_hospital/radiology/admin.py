from django.contrib import admin
from radiology.models import RadiologyTest


@admin.register(RadiologyTest)
class RadiologyTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'report_type', 'price', 'is_active')
    list_filter = ('department', 'report_type', 'is_active')
    search_fields = ('name',)
