from django.contrib import admin
from patients.models import Province, District, InsuranceCompany, InsuranceCategory, Patient, Visit


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('number', 'name')
    ordering = ('number',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'province')
    list_filter = ('province',)
    search_fields = ('name',)


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(InsuranceCategory)
class InsuranceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'coverage_percent', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name', 'company__name')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_code', 'full_name', 'gender', 'age', 'age_at_registration', 'phone_number', 'district', 'has_insurance', 'created_at')
    list_filter = ('gender', 'has_insurance', 'district__province')
    search_fields = ('patient_code', 'first_name', 'last_name', 'phone_number', 'citizenship_number')
    readonly_fields = ('patient_code', 'qr_code')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'patient', 'department', 'doctor', 'patient_type', 'registration_fee', 'visit_date', 'token_number')
    list_filter = ('patient_type', 'department', 'visit_date')
    search_fields = ('receipt_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('receipt_number', 'token_number')
