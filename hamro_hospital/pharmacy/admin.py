from django.contrib import admin, messages
from pharmacy.models import Medicine, StockAdjustment, PharmacySale, PharmacySaleItem


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('medicine_code', 'name', 'category', 'selling_price', 'current_stock', 'minimum_stock', 'expiry_date', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('medicine_code', 'name', 'generic_name', 'brand_name')


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'quantity_change', 'reason', 'resulting_stock', 'adjusted_by', 'created_at')
    list_filter = ('reason', 'created_at')
    readonly_fields = ('resulting_stock', 'adjusted_by')

    def save_model(self, request, obj, form, change):
        if not obj.adjusted_by_id:
            obj.adjusted_by = request.user
        try:
            super().save_model(request, obj, form, change)
        except ValueError as exc:
            messages.error(request, str(exc))

    def has_change_permission(self, request, obj=None):
        return False


class PharmacySaleItemInline(admin.TabularInline):
    model = PharmacySaleItem
    extra = 1
    # medicine_name/unit_price are filled from selected medicine on save.
    readonly_fields = ()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in {'medicine_name', 'unit_price'}:
            formfield.required = False
            formfield.help_text = 'Leave blank to copy from selected medicine.'
        return formfield


@admin.register(PharmacySale)
class PharmacySaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'patient', 'prescription_source', 'payment_method', 'total_amount', 'sold_by', 'created_at')
    list_filter = ('prescription_source', 'payment_method')
    search_fields = ('sale_number', 'patient__patient_code')
    readonly_fields = ('sale_number', 'total_amount', 'sold_by', 'barcode')
    inlines = [PharmacySaleItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.sold_by_id:
            obj.sold_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, PharmacySaleItem) and obj.medicine_id:
                if not obj.medicine_name:
                    obj.medicine_name = obj.medicine.name
                if not obj.unit_price:
                    obj.unit_price = obj.medicine.selling_price
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
        if isinstance(form.instance, PharmacySale):
            form.instance.recalculate_total()
