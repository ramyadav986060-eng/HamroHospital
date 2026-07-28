from django.contrib import admin
from billing.models import Bill, BillItem, ReprintLog, RefundRequest, DiscountRequest


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ('service_name', 'unit_price')


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'patient', 'payment_method', 'total_amount', 'status', 'cashier', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('bill_number', 'patient__patient_code', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('bill_number', 'total_amount')
    inlines = [BillItemInline]


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


@admin.register(DiscountRequest)
class DiscountRequestAdmin(admin.ModelAdmin):
    list_display = ('bill', 'original_amount', 'discount_amount', 'payable_amount', 'reason', 'status', 'requested_by', 'requested_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('bill__bill_number', 'bill__patient__patient_code', 'bill__patient__first_name', 'bill__patient__last_name', 'reason')
    readonly_fields = ('requested_at', 'reviewed_at')
