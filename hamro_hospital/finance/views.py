import datetime

from django.db.models import Sum
from django.shortcuts import render

from accounts.decorators import accounts_dept_required
from billing.models import Bill, RefundRequest, DiscountRequest


def _apply_date_filter(qs, request, field='created_at__date'):
    today = datetime.date.today()
    date_filter = request.GET.get('date_filter', 'month')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    if date_filter == 'today':
        qs = qs.filter(**{field: today})
    elif date_filter == 'week':
        qs = qs.filter(**{f'{field}__gte': today - datetime.timedelta(days=today.weekday())})
    elif date_filter == 'month':
        qs = qs.filter(**{f'{field}__gte': today.replace(day=1)})
    elif date_filter == 'year':
        qs = qs.filter(**{f'{field}__gte': today.replace(month=1, day=1)})
    elif date_filter == 'custom':
        try:
            if start_date_str:
                qs = qs.filter(**{f'{field}__gte': datetime.date.fromisoformat(start_date_str)})
            if end_date_str:
                qs = qs.filter(**{f'{field}__lte': datetime.date.fromisoformat(end_date_str)})
        except ValueError:
            pass
    # all = no filter
    return qs, date_filter, start_date_str, end_date_str


@accounts_dept_required
def dashboard(request):
    today = datetime.date.today()
    paid_bills = Bill.objects.filter(status=Bill.Status.PAID)
    filtered_bills, date_filter, start_date, end_date = _apply_date_filter(paid_bills, request)
    todays_bills = paid_bills.filter(created_at__date=today)

    revenue_by_type = {
        bt: filtered_bills.filter(bill_type=bt).aggregate(total=Sum('total_amount'))['total'] or 0
        for bt, _ in Bill._meta.get_field('bill_type').choices
    }

    return render(request, 'finance/dashboard.html', {
        'date_filter': date_filter,
        'start_date': start_date,
        'end_date': end_date,
        'todays_total': todays_bills.aggregate(total=Sum('total_amount'))['total'] or 0,
        'filtered_total': filtered_bills.aggregate(total=Sum('total_amount'))['total'] or 0,
        'month_total': paid_bills.filter(created_at__date__gte=today.replace(day=1)).aggregate(total=Sum('total_amount'))['total'] or 0,
        'revenue_by_type': revenue_by_type,
        'pending_refunds_count': RefundRequest.objects.filter(status=RefundRequest.Status.PENDING).count(),
        'pending_discounts_count': DiscountRequest.objects.filter(status=DiscountRequest.Status.PENDING).count(),
    })
