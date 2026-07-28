from django.contrib import admin
from radiology.models import RadiologyTest, RadiologyReportTemplate


@admin.register(RadiologyTest)
class RadiologyTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'report_type', 'price', 'is_active')
    list_filter = ('department', 'report_type', 'is_active')
    search_fields = ('name',)


@admin.register(RadiologyReportTemplate)
class RadiologyReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_type', 'is_active')
    list_filter = ('service_type', 'is_active')
    search_fields = ('name', 'findings_template', 'impression_template')
