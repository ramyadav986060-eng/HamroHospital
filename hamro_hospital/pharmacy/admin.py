from django.contrib import admin
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
    readonly_fields = ('resulting_stock',)

    def has_change_permission(self, request, obj=None):
        return False


class PharmacySaleItemInline(admin.TabularInline):
    model = PharmacySaleItem
    extra = 0
    readonly_fields = ('medicine_name', 'unit_price')


@admin.register(PharmacySale)
class PharmacySaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'patient', 'prescription_source', 'payment_method', 'total_amount', 'sold_by', 'created_at')
    list_filter = ('prescription_source', 'payment_method')
    search_fields = ('sale_number', 'patient__patient_code')
    readonly_fields = ('sale_number', 'total_amount')
    inlines = [PharmacySaleItemInline]
