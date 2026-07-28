from django.contrib import admin
from operation_theatre.models import OTRoom, Surgery, OperationType


@admin.register(OperationType)
class OperationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'fixed_price', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('name',)


@admin.register(OTRoom)
class OTRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')


@admin.register(Surgery)
class SurgeryAdmin(admin.ModelAdmin):
    list_display = ('surgery_number', 'patient', 'surgery_name', 'operation_type', 'surgeon', 'status', 'scheduled_datetime')
    list_filter = ('status', 'ot_room')
    search_fields = ('surgery_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('surgery_number', 'created_by', 'barcode')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
