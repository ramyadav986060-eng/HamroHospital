import datetime

from django.db.models import Sum
from django.shortcuts import render

from accounts.decorators import accounts_dept_required
from billing.models import Bill, RefundRequest, DiscountRequest


@accounts_dept_required
def dashboard(request):
    today = datetime.date.today()
    month_start = today.replace(day=1)

    todays_bills = Bill.objects.filter(created_at__date=today, status=Bill.Status.PAID)
    month_bills = Bill.objects.filter(created_at__date__gte=month_start, status=Bill.Status.PAID)

    revenue_by_type = {
        bt: month_bills.filter(bill_type=bt).aggregate(total=Sum('total_amount'))['total'] or 0
        for bt, _ in Bill._meta.get_field('bill_type').choices
    }

    return render(request, 'finance/dashboard.html', {
        'todays_total': todays_bills.aggregate(total=Sum('total_amount'))['total'] or 0,
        'month_total': month_bills.aggregate(total=Sum('total_amount'))['total'] or 0,
        'revenue_by_type': revenue_by_type,
        'pending_refunds_count': RefundRequest.objects.filter(status=RefundRequest.Status.PENDING).count(),
        'pending_discounts_count': DiscountRequest.objects.filter(status=DiscountRequest.Status.PENDING).count(),
    })
