import datetime

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required, pharmacy_required
from accounts.models import AuditLog
from accounts.utils import write_audit_log
from pharmacy.forms import MedicineForm, StockAdjustmentForm, PharmacySaleForm
from pharmacy.models import Medicine, StockAdjustment, PharmacySale, PharmacySaleItem
from patients.models import Patient
from consultations.models import Consultation


# --- Super Admin: Medicine catalogue -----------------------------------------

@super_admin_required
def medicine_list(request):
    medicines = Medicine.objects.all()
    return render(request, 'pharmacy/medicine_list.html', {'medicines': medicines})


@super_admin_required
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f'Medicine "{medicine.name}" added.')
            return redirect('pharmacy:medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': 'Add Medicine'})


@super_admin_required
def medicine_edit(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medicine "{medicine.name}" updated.')
            return redirect('pharmacy:medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'pharmacy/medicine_form.html', {'form': form, 'title': f'Edit {medicine.name}', 'medicine': medicine})


@super_admin_required
def stock_adjust(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                adjustment = form.save(commit=False)
                adjustment.medicine = medicine
                adjustment.adjusted_by = request.user
                adjustment.save()
                write_audit_log(
                    request, AuditLog.Action.STOCK_ADJUSTED,
                    f"Stock adjusted for {medicine.name}: {adjustment.quantity_change:+d} ({adjustment.get_reason_display()})",
                )
                messages.success(request, f'Stock updated. New stock: {adjustment.resulting_stock}')
                return redirect('pharmacy:medicine_list')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = StockAdjustmentForm()
    return render(request, 'pharmacy/stock_adjust.html', {'form': form, 'medicine': medicine})


# --- Pharmacy role: dispensing workflow ---------------------------------------

@pharmacy_required
def dashboard(request):
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    todays_sales = PharmacySale.objects.filter(created_at__date=today)
    totals_by_method = {
        method: todays_sales.filter(payment_method=method).aggregate(total=Sum('total_amount'))['total'] or 0
        for method, _ in PharmacySale.PaymentMethod.choices
    }
    monthly_sales = PharmacySale.objects.filter(created_at__date__gte=month_start)
    yearly_sales = PharmacySale.objects.filter(created_at__date__gte=year_start)
    active_medicines = Medicine.objects.filter(is_active=True)
    return render(request, 'pharmacy/dashboard.html', {
        'todays_count': todays_sales.count(),
        'todays_total': sum(totals_by_method.values()),
        'totals_by_method': totals_by_method,
        'monthly_count': monthly_sales.count(),
        'monthly_total': monthly_sales.aggregate(t=Sum('total_amount'))['t'] or 0,
        'yearly_count': yearly_sales.count(),
        'yearly_total': yearly_sales.aggregate(t=Sum('total_amount'))['t'] or 0,
        'low_stock_count': sum(1 for m in active_medicines if m.is_low_stock),
        'out_of_stock_count': active_medicines.filter(current_stock=0).count(),
    })


@pharmacy_required
def patient_lookup(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        )
    return render(request, 'pharmacy/patient_lookup.html', {'q': q, 'patients': patients})


@pharmacy_required
def dispense(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    medicines = Medicine.objects.filter(is_active=True)

    # Pull the most recent consultation's prescription for convenience (Digital source)
    latest_consultation = (
        Consultation.objects.filter(visit__patient=patient).order_by('-created_at').first()
    )

    if request.method == 'POST':
        sale_form = PharmacySaleForm(request.POST, request.FILES)
        selected_ids = request.POST.getlist('medicine_id')
        quantities = {mid: int(request.POST.get(f'quantity_{mid}', 1) or 1) for mid in selected_ids}

        if not selected_ids:
            messages.error(request, 'Select at least one medicine to dispense.')
        elif sale_form.is_valid():
            # Validate stock before committing anything
            insufficient = []
            for mid in selected_ids:
                medicine = medicines.get(pk=mid)
                if medicine.current_stock < quantities[mid]:
                    insufficient.append(medicine.name)
            if insufficient:
                messages.error(request, f"Insufficient stock for: {', '.join(insufficient)}")
            else:
                with transaction.atomic():
                    sale = PharmacySale.objects.create(
                        patient=patient,
                        consultation=latest_consultation if sale_form.cleaned_data['prescription_source'] == 'digital' else None,
                        prescription_source=sale_form.cleaned_data['prescription_source'],
                        manual_prescription_copy=sale_form.cleaned_data.get('manual_prescription_copy'),
                        payment_method=sale_form.cleaned_data['payment_method'],
                        insurance_company=sale_form.cleaned_data.get('insurance_company')
                        if sale_form.cleaned_data['payment_method'] == 'insurance' else None,
                        sold_by=request.user,
                    )
                    for mid in selected_ids:
                        medicine = Medicine.objects.select_for_update().get(pk=mid)
                        qty = quantities[mid]
                        medicine.current_stock -= qty
                        medicine.save(update_fields=['current_stock'])
                        PharmacySaleItem.objects.create(
                            sale=sale, medicine=medicine, medicine_name=medicine.name,
                            unit_price=medicine.selling_price, quantity=qty,
                        )
                    sale.recalculate_total()

                write_audit_log(
                    request, AuditLog.Action.PHARMACY_SALE,
                    f"Pharmacy sale for {patient.full_name}",
                    patient_id_text=patient.patient_code, receipt_number=sale.sale_number,
                    amount=sale.total_amount, payment_method=sale.get_payment_method_display(),
                )
                messages.success(request, f'Sale {sale.sale_number} completed.')
                return redirect('pharmacy:receipt', pk=sale.pk)
    else:
        sale_form = PharmacySaleForm()

    return render(request, 'pharmacy/dispense.html', {
        'patient': patient, 'medicines': medicines, 'sale_form': sale_form,
        'latest_consultation': latest_consultation,
    })


@pharmacy_required
def receipt(request, pk):
    sale = get_object_or_404(PharmacySale.objects.select_related('patient', 'sold_by').prefetch_related('items'), pk=pk)
    return render(request, 'pharmacy/receipt.html', {'sale': sale})


@pharmacy_required
def reprint_receipt(request, pk):
    sale = get_object_or_404(PharmacySale.objects.select_related('patient', 'sold_by').prefetch_related('items'), pk=pk)
    write_audit_log(
        request, AuditLog.Action.REPRINT, f"Reprinted pharmacy receipt {sale.sale_number}",
        patient_id_text=sale.patient.patient_code if sale.patient else '', receipt_number=sale.sale_number,
    )
    return render(request, 'pharmacy/receipt.html', {'sale': sale, 'is_reprint': True})


@pharmacy_required
def todays_sales(request):
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except ValueError:
        selected_date = datetime.date.today()

    sales = PharmacySale.objects.filter(sold_by=request.user, created_at__date=selected_date).select_related('patient')
    totals_by_method = {
        method: sales.filter(payment_method=method).aggregate(total=Sum('total_amount'))['total'] or 0
        for method, _ in PharmacySale.PaymentMethod.choices
    }
    return render(request, 'pharmacy/todays_sales.html', {
        'sales': sales, 'totals_by_method': totals_by_method, 'grand_total': sum(totals_by_method.values()),
        'selected_date': selected_date, 'is_today': selected_date == datetime.date.today(),
    })
