from django.contrib import admin
from billing.models import Bill, BillItem, ReprintLog, RefundRequest, DiscountRequest


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1
    # service_name and unit_price are snapshots. They are filled from the
    # selected service automatically when saved through Django Admin.
    readonly_fields = ()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in {'service_name', 'unit_price'}:
            formfield.required = False
            formfield.help_text = 'Leave blank to copy from selected service.'
        return formfield


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'patient', 'payment_method', 'total_amount', 'status', 'cashier', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('bill_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('bill_number', 'total_amount', 'barcode')
    inlines = [BillItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.cashier_id:
            obj.cashier = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, BillItem) and obj.service_id:
                if not obj.service_name:
                    obj.service_name = obj.service.name
                if not obj.unit_price:
                    obj.unit_price = obj.service.price
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
        if isinstance(form.instance, Bill):
            form.instance.recalculate_total()


@admin.register(ReprintLog)
class ReprintLogAdmin(admin.ModelAdmin):
    list_display = ('bill', 'reprinted_by', 'reprinted_at')
    readonly_fields = ('bill', 'reprinted_by', 'reprinted_at')

    def has_add_permission(self, request):
        return False


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('bill', 'amount', 'status', 'requested_by', 'requested_at', 'reviewed_by')
    list_filter = ('status', 'requested_at')
    search_fields = ('bill__bill_number', 'bill__patient__patient_code', 'bill__patient__first_name', 'bill__patient__last_name')
    readonly_fields = ('requested_at', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if not obj.requested_by_id:
            obj.requested_by = request.user
        if obj.status != obj.Status.PENDING and not obj.reviewed_by_id:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DiscountRequest)
class DiscountRequestAdmin(admin.ModelAdmin):
    list_display = ('bill', 'original_amount', 'discount_amount', 'payable_amount', 'reason', 'status', 'requested_by', 'requested_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('bill__bill_number', 'bill__patient__patient_code', 'bill__patient__first_name', 'bill__patient__last_name', 'reason')
    readonly_fields = ('requested_at', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if not obj.requested_by_id:
            obj.requested_by = request.user
        if obj.status != obj.Status.PENDING and not obj.approved_by_id:
            obj.approved_by = request.user
        super().save_model(request, obj, form, change)
