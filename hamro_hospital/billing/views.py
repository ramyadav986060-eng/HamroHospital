import datetime

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.decorators import cash_counter_required, billing_counter_required, accounts_dept_required, role_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log
from billing.forms import (
    PatientLookupForm, BillPaymentForm, RefundRequestForm, RefundReviewForm,
    DiscountRequestForm, DiscountReviewForm,
)
from billing.models import Bill, BillItem, ReprintLog, PaymentMethod, RefundRequest, DiscountRequest
from patients.models import Patient
from website.models import HospitalService


@cash_counter_required
def dashboard(request):
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    todays_bills = Bill.objects.filter(created_at__date=today, status=Bill.Status.PAID)
    totals_by_method = {
        method: todays_bills.filter(payment_method=method).aggregate(total=Sum('total_amount'))['total'] or 0
        for method, _ in PaymentMethod.choices
    }
    monthly_bills = Bill.objects.filter(created_at__date__gte=month_start, status=Bill.Status.PAID)
    yearly_bills = Bill.objects.filter(created_at__date__gte=year_start, status=Bill.Status.PAID)

    return render(request, 'billing/dashboard.html', {
        'todays_bills': todays_bills.select_related('patient'),
        'todays_count': todays_bills.count(),
        'todays_total': sum(totals_by_method.values()),
        'totals_by_method': totals_by_method,
        'monthly_count': monthly_bills.count(),
        'monthly_total': monthly_bills.aggregate(t=Sum('total_amount'))['t'] or 0,
        'yearly_count': yearly_bills.count(),
        'yearly_total': yearly_bills.aggregate(t=Sum('total_amount'))['t'] or 0,
    })


@cash_counter_required
def patient_lookup(request):
    form = PatientLookupForm(request.GET or None)
    patients = Patient.objects.none()
    if form.is_valid() and form.cleaned_data['q']:
        q = form.cleaned_data['q']
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).select_related('district', 'insurance_company')
    return render(request, 'billing/patient_lookup.html', {'form': form, 'patients': patients})


@billing_counter_required
def create_bill(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    services = HospitalService.objects.filter(is_active=True)

    from patients.models import Visit
    from consultations.models import LabTestRequest, RadiologyRequest, RequestStatus
    from operation_theatre.models import Surgery

    # Laboratory/Radiology staff may only use this screen to bill their own
    # department's pending items (spec 5: "Laboratory billing must not
    # include admission, pharmacy, OT, or radiology payments" - spec 6
    # mirrors this for Radiology). Cashier/Super Admin get full access.
    counter_department = None
    if request.user.role == Role.LABORATORY and not request.user.is_superuser:
        counter_department = 'laboratory'
    elif request.user.role == Role.RADIOLOGY and not request.user.is_superuser:
        counter_department = 'radiology'

    # Load pending items
    pending_visits = Visit.objects.filter(patient=patient, payment_status=Visit.PaymentStatus.PENDING)
    pending_labs = LabTestRequest.objects.filter(
        Q(consultation__visit__patient=patient) | Q(patient=patient), status=RequestStatus.REQUESTED
    )
    pending_radiologies = RadiologyRequest.objects.filter(
        Q(consultation__visit__patient=patient) | Q(patient=patient), status=RequestStatus.REQUESTED
    )
    pending_surgeries = Surgery.objects.filter(patient=patient, status=Surgery.Status.SCHEDULED)

    if counter_department == 'laboratory':
        services = services.none()
        pending_visits = pending_visits.none()
        pending_radiologies = pending_radiologies.none()
        pending_surgeries = pending_surgeries.none()
    elif counter_department == 'radiology':
        services = services.none()
        pending_visits = pending_visits.none()
        pending_labs = pending_labs.none()
        pending_surgeries = pending_surgeries.none()

    # Full patient snapshot for Cash Counter (spec section 2): previous
    # billing history, insurance status, and current admission status,
    # shown alongside the Patient ID/QR code before a new bill is created.
    from admissions.models import Admission
    billing_history = Bill.objects.filter(patient=patient).order_by('-created_at')[:10]
    current_admission = Admission.objects.filter(
        patient=patient, status=Admission.Status.ADMITTED,
    ).select_related('ward', 'bed', 'department').first()

    if counter_department == 'laboratory':
        bill_type = 'lab'
    elif counter_department == 'radiology':
        bill_type = 'radiology'
    else:
        bill_type = request.POST.get('bill_type') or request.GET.get('bill_type', 'opd')
    admission_id = request.POST.get('admission_id') or request.GET.get('admission_id')
    surgery_id = request.POST.get('surgery_id') or request.GET.get('surgery_id')

    if request.method == 'POST':
        payment_form = BillPaymentForm(request.POST)
        selected_service_ids = request.POST.getlist('service_id')
        quantities = {sid: int(request.POST.get(f'quantity_{sid}', 1) or 1) for sid in selected_service_ids}

        pending_visit_ids = request.POST.getlist('pending_visit')
        pending_lab_ids = request.POST.getlist('pending_lab')
        pending_radiology_ids = request.POST.getlist('pending_radiology')
        pending_surgery_ids = request.POST.getlist('pending_surgery')

        has_pending_selection = bool(pending_visit_ids or pending_lab_ids or pending_radiology_ids or pending_surgery_ids)

        if not selected_service_ids and not has_pending_selection:
            messages.error(request, 'Select at least one service or pending doctor order to bill.')
        elif payment_form.is_valid():
            if counter_department == 'laboratory':
                forced_counter_name = 'Laboratory Counter'
            elif counter_department == 'radiology':
                forced_counter_name = 'Radiology Counter'
            else:
                forced_counter_name = payment_form.cleaned_data.get('counter_name') or 'Main Cash Counter'
            bill = Bill.objects.create(
                patient=patient, cashier=request.user,
                bill_type=bill_type if bill_type in dict(Bill._meta.get_field('bill_type').choices) else 'opd',
                admission_id=admission_id or None,
                surgery_id=surgery_id or None,
                counter_name=forced_counter_name,
                payment_method=payment_form.cleaned_data['payment_method'],
                insurance_company=payment_form.cleaned_data.get('insurance_company')
                if payment_form.cleaned_data['payment_method'] == PaymentMethod.INSURANCE else None,
                insurance_coverage_amount=payment_form.cleaned_data.get('insurance_coverage_amount') or 0
                if payment_form.cleaned_data['payment_method'] == PaymentMethod.INSURANCE else 0,
            )
            # 1. Process standard services
            for sid in selected_service_ids:
                service = services.get(pk=sid)
                BillItem.objects.create(
                    bill=bill, service=service, service_name=service.name,
                    unit_price=service.price, quantity=quantities.get(sid, 1),
                )
            
            # 2. Process pending visits
            for vid in pending_visit_ids:
                v = pending_visits.filter(pk=vid).first()
                if v:
                    BillItem.objects.create(
                        bill=bill, service=None, service_name=f"OPD Registration Fee ({v.receipt_number})",
                        unit_price=v.registration_fee, quantity=1,
                    )
                    v.payment_status = Visit.PaymentStatus.PAID
                    v.save()

            # 3. Process pending labs
            for lid in pending_lab_ids:
                l = pending_labs.filter(pk=lid).first()
                if l:
                    svc = services.filter(name__icontains=l.test_name).first()
                    price = svc.price if svc else 300
                    BillItem.objects.create(
                        bill=bill, service=svc, service_name=f"Lab Test: {l.test_name}",
                        unit_price=price, quantity=1,
                    )
                    l.status = RequestStatus.ACCEPTED
                    l.accepted_at = l.accepted_at or timezone.now()
                    l.accepted_by = l.accepted_by or request.user
                    l.save()

            # 4. Process pending radiologies
            for rid in pending_radiology_ids:
                r = pending_radiologies.filter(pk=rid).first()
                if r:
                    svc = services.filter(name__icontains=r.display_service_name).first()
                    price = svc.price if svc else 500
                    BillItem.objects.create(
                        bill=bill, service=svc, service_name=f"Radiology: {r.display_service_name}",
                        unit_price=price, quantity=1,
                    )
                    r.status = RequestStatus.ACCEPTED
                    r.accepted_at = r.accepted_at or timezone.now()
                    r.accepted_by = r.accepted_by or request.user
                    r.save()

            # 5. Process pending surgeries
            for sid in pending_surgery_ids:
                s = pending_surgeries.filter(pk=sid).first()
                if s:
                    BillItem.objects.create(
                        bill=bill, service=None, service_name=f"Surgery: {s.surgery_name} ({s.surgery_number})",
                        unit_price=s.charge_amount, quantity=1,
                    )
                    s.status = Surgery.Status.IN_PROGRESS
                    s.save()

            bill.recalculate_total()

            write_audit_log(
                request, AuditLog.Action.PAYMENT,
                f"Bill created for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=bill.bill_number,
                amount=bill.total_amount, payment_method=bill.get_payment_method_display(),
            )

            # Trigger real-time notifications
            from accounts.utils import create_notification
            create_notification(
                title="Payment Completed",
                message=f"Payment received for bill {bill.bill_number}. Total amount: NPR {bill.total_amount}.",
                role=Role.CASH_COUNTER
            )
            for vid in pending_visit_ids:
                create_notification(
                    title="Payment Completed",
                    message=f"Registration fee paid for {patient.full_name} OPD visit.",
                    role=Role.REGISTRATION_COUNTER
                )
            for lid in pending_lab_ids:
                create_notification(
                    title="Lab Request Assigned",
                    message=f"Laboratory test has been paid and is ready for {patient.full_name}.",
                    role=Role.LABORATORY
                )
            for rid in pending_radiology_ids:
                create_notification(
                    title="Radiology Request Assigned",
                    message=f"Radiology imaging has been paid and is ready for {patient.full_name}.",
                    role=Role.RADIOLOGY
                )
            for sid in pending_surgery_ids:
                create_notification(
                    title="Operation Scheduled",
                    message=f"Surgery record has been paid and is ready for {patient.full_name}.",
                    role=Role.OPERATION_THEATRE
                )

            messages.success(request, f'Bill {bill.bill_number} created.')
            return redirect('billing:receipt', pk=bill.pk)
    else:
        payment_form = BillPaymentForm()

    return render(request, 'billing/create_bill.html', {
        'patient': patient, 'services': services, 'payment_form': payment_form,
        'bill_type': bill_type, 'admission_id': admission_id, 'surgery_id': surgery_id,
        'billing_history': billing_history, 'current_admission': current_admission,
        'pending_visits': pending_visits, 'pending_labs': pending_labs,
        'pending_radiologies': pending_radiologies, 'pending_surgeries': pending_surgeries,
        'counter_department': counter_department,
    })


@cash_counter_required
def edit_bill(request, pk):
    bill = get_object_or_404(Bill.objects.prefetch_related('items'), pk=pk)
    patient = bill.patient
    services = HospitalService.objects.filter(is_active=True)

    # Check 24-hour limit and "own bill" rule
    from django.utils import timezone
    import datetime
    
    if (timezone.now() - bill.created_at) > datetime.timedelta(hours=24):
        if not request.user.is_superuser:
            messages.error(request, "This bill is older than 24 hours. Only a Super Admin can edit it.")
            return redirect('billing:receipt', pk=bill.pk)
            
    if bill.cashier and bill.cashier != request.user:
        if not request.user.is_superuser:
            messages.error(request, "You can only edit your own bills.")
            return redirect('billing:receipt', pk=bill.pk)

    if request.method == 'POST':
        selected_service_ids = request.POST.getlist('service_id')
        quantities = {sid: int(request.POST.get(f'quantity_{sid}', 1) or 1) for sid in selected_service_ids}

        if not selected_service_ids:
            messages.error(request, 'Select at least one service to bill.')
        else:
            # Delete old items and add new items
            bill.items.all().delete()
            for sid in selected_service_ids:
                service = services.get(pk=sid)
                BillItem.objects.create(
                    bill=bill, service=service, service_name=service.name,
                    unit_price=service.price, quantity=quantities.get(sid, 1),
                )
            bill.recalculate_total()
            
            write_audit_log(
                request, AuditLog.Action.PAYMENT,
                f"Bill edited: {bill.bill_number} for {patient.full_name}",
                patient_id_text=patient.patient_code, receipt_number=bill.bill_number,
                amount=bill.total_amount,
            )
            messages.success(request, f'Bill {bill.bill_number} edited successfully.')
            return redirect('billing:receipt', pk=bill.pk)

    # For GET, pre-populate selected items
    bill_items = bill.items.all()
    selected_service_ids = {item.service_id: item for item in bill_items}
    
    annotated_services = []
    for s in services:
        is_selected = s.id in selected_service_ids
        qty = selected_service_ids[s.id].quantity if is_selected else 1
        annotated_services.append({
            'id': s.id,
            'name': s.name,
            'service_code': s.service_code,
            'price': s.price,
            'is_selected': is_selected,
            'quantity': qty,
        })
    
    return render(request, 'billing/edit_bill.html', {
        'bill': bill,
        'patient': patient,
        'services': annotated_services,
    })


def num_to_words(num):
    try:
        num = int(float(num))
    except (ValueError, TypeError):
        return "Zero Rupees Only"
    
    if num == 0:
        return "Zero Rupees Only"
        
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", 
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert(n):
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 else "")
        elif n < 1000:
            return units[n // 100] + " Hundred" + (" and " + convert(n % 100) if n % 100 else "")
        elif n < 100000:
            return convert(n // 1000) + " Thousand" + (" " + convert(n % 1000) if n % 1000 else "")
        elif n < 10000000:
            return convert(n // 100000) + " Lakh" + (" " + convert(n % 100000) if n % 100000 else "")
        else:
            return convert(n // 10000000) + " Crore" + (" " + convert(n % 10000000) if n % 10000000 else "")

    words = convert(num)
    return f"{words} Rupees Only."


@billing_counter_required
def receipt(request, pk):
    bill = get_object_or_404(Bill.objects.select_related('patient', 'cashier', 'insurance_company').prefetch_related('items'), pk=pk)
    amount_words = num_to_words(bill.final_amount_paid)
    return render(request, 'billing/receipt.html', {'bill': bill, 'amount_in_words': amount_words})


@cash_counter_required
def reprint_receipt(request, pk):
    bill = get_object_or_404(Bill.objects.select_related('patient', 'cashier').prefetch_related('items'), pk=pk)
    ReprintLog.objects.create(bill=bill, reprinted_by=request.user)
    write_audit_log(
        request, AuditLog.Action.REPRINT, f"Reprinted bill {bill.bill_number}",
        patient_id_text=bill.patient.patient_code, receipt_number=bill.bill_number,
    )
    amount_words = num_to_words(bill.final_amount_paid)
    return render(request, 'billing/receipt.html', {'bill': bill, 'is_reprint': True, 'amount_in_words': amount_words})


@cash_counter_required
def todays_collections(request):
    date_str = request.GET.get('date', '')
    try:
        selected_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except ValueError:
        selected_date = datetime.date.today()

    bills = Bill.objects.filter(
        cashier=request.user, created_at__date=selected_date, status=Bill.Status.PAID,
    ).select_related('patient')
    totals_by_method = {
        method: bills.filter(payment_method=method).aggregate(total=Sum('total_amount'))['total'] or 0
        for method, _ in PaymentMethod.choices
    }
    return render(request, 'billing/todays_collections.html', {
        'bills': bills, 'totals_by_method': totals_by_method, 'grand_total': sum(totals_by_method.values()),
        'selected_date': selected_date, 'is_today': selected_date == datetime.date.today(),
    })


@cash_counter_required
def refund_request(request, pk):
    bill = get_object_or_404(Bill.objects.select_related('patient'), pk=pk, status=Bill.Status.PAID)
    if request.method == 'POST':
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            refund = RefundRequest.objects.create(
                bill=bill, amount=form.cleaned_data['amount'], reason=form.cleaned_data['reason'],
                requested_by=request.user,
            )
            write_audit_log(
                request, AuditLog.Action.REFUND_REQUESTED,
                f"Refund requested for bill {bill.bill_number}",
                patient_id_text=bill.patient.patient_code, receipt_number=bill.bill_number,
                amount=refund.amount,
            )
            messages.success(request, 'Refund request submitted for Accounts approval.')
            return redirect('billing:receipt', pk=bill.pk)
    else:
        form = RefundRequestForm(initial={'amount': bill.total_amount})
    return render(request, 'billing/refund_request.html', {'form': form, 'bill': bill})


@accounts_dept_required
def refund_review_list(request):
    refunds = RefundRequest.objects.select_related('bill__patient', 'requested_by').filter(
        status=RefundRequest.Status.PENDING,
    )
    return render(request, 'billing/refund_review_list.html', {'refunds': refunds})


@accounts_dept_required
def refund_review(request, pk):
    refund = get_object_or_404(RefundRequest.objects.select_related('bill__patient'), pk=pk)
    if request.method == 'POST':
        form = RefundReviewForm(request.POST)
        decision = request.POST.get('decision')
        if form.is_valid() and decision in ('approve', 'reject'):
            notes = form.cleaned_data['review_notes']
            if decision == 'approve':
                refund.approve(request.user, notes)
                action_desc = f"Refund approved for bill {refund.bill.bill_number}"
            else:
                refund.reject(request.user, notes)
                action_desc = f"Refund rejected for bill {refund.bill.bill_number}"
            write_audit_log(
                request, AuditLog.Action.REFUND_REVIEWED, action_desc,
                patient_id_text=refund.bill.patient.patient_code, receipt_number=refund.bill.bill_number,
                amount=refund.amount,
            )
            messages.success(request, action_desc + '.')
            return redirect('billing:refund_review_list')
    else:
        form = RefundReviewForm()
    return render(request, 'billing/refund_review.html', {'refund': refund, 'form': form})


@cash_counter_required
def discount_request(request, pk):
    """Cash Counter requests a 'Poor Patient' discount against a paid bill (spec section 7)."""
    bill = get_object_or_404(Bill.objects.select_related('patient'), pk=pk, status=Bill.Status.PAID)
    if request.method == 'POST':
        form = DiscountRequestForm(request.POST)
        if form.is_valid():
            discount = DiscountRequest.objects.create(
                bill=bill, original_amount=bill.total_amount,
                discount_amount=form.cleaned_data['discount_amount'],
                reason=form.cleaned_data['reason'], remarks=form.cleaned_data['remarks'],
                requested_by=request.user,
            )
            write_audit_log(
                request, AuditLog.Action.OTHER,
                f"Discount requested for bill {bill.bill_number}: {discount.reason}",
                patient_id_text=bill.patient.patient_code, receipt_number=bill.bill_number,
                amount=discount.discount_amount,
            )
            messages.success(request, 'Discount request submitted for Accounts approval.')
            return redirect('billing:receipt', pk=bill.pk)
    else:
        form = DiscountRequestForm()
    return render(request, 'billing/discount_request.html', {'form': form, 'bill': bill})


@accounts_dept_required
def discount_review_list(request):
    discounts = DiscountRequest.objects.select_related('bill__patient', 'requested_by').filter(
        status=DiscountRequest.Status.PENDING,
    )
    return render(request, 'billing/discount_review_list.html', {'discounts': discounts})


@accounts_dept_required
def discount_review(request, pk):
    discount = get_object_or_404(DiscountRequest.objects.select_related('bill__patient'), pk=pk)
    if request.method == 'POST':
        form = DiscountReviewForm(request.POST)
        decision = request.POST.get('decision')
        if form.is_valid() and decision in ('approve', 'reject'):
            notes = form.cleaned_data['review_notes']
            if decision == 'approve':
                discount.approve(request.user, notes)
                action_desc = f"Discount approved for bill {discount.bill.bill_number}"
            else:
                discount.reject(request.user, notes)
                action_desc = f"Discount rejected for bill {discount.bill.bill_number}"
            write_audit_log(
                request, AuditLog.Action.OTHER, action_desc,
                patient_id_text=discount.bill.patient.patient_code, receipt_number=discount.bill.bill_number,
                amount=discount.discount_amount,
            )
            messages.success(request, action_desc + '.')
            return redirect('billing:discount_review_list')
    else:
        form = DiscountReviewForm()
    return render(request, 'billing/discount_review.html', {'discount': discount, 'form': form})


@role_required(Role.SUPER_ADMIN, Role.CASH_COUNTER, Role.ACCOUNTS_DEPT)
def invoice_pdf(request, pk):
    """
    Downloadable PDF invoice for a bill - available to Cash Counter,
    Accounts, and Super Admin. Built with reportlab (already a project
    dependency, used elsewhere for QR/report generation).

    NOTE: The primary "Download PDF" button on the invoice page now
    generates the PDF client-side from the exact rendered HTML (see
    static/js/print_tools.js + templates/includes/print_actions.html),
    so the download always looks identical to the on-screen/printed
    invoice. This server-side route is kept as a lightweight fallback
    URL (e.g. for direct linking/automation) but is intentionally
    plainer and is not linked from the main invoice action bar.
    """
    import io
    from django.conf import settings
    from django.http import FileResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    bill = get_object_or_404(Bill.objects.select_related('patient').prefetch_related('items'), pk=pk)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    logo_path = settings.BASE_DIR / 'static' / 'images' / 'hospital_logo.png'
    if logo_path.exists():
        p.drawImage(ImageReader(str(logo_path)), 50, y - 30, width=50, height=50, mask='auto')
        text_x = 110
    else:
        text_x = 50

    p.setFont('Helvetica-Bold', 16)
    p.drawString(text_x, y, settings.HOSPITAL_NAME)
    y -= 16
    p.setFont('Helvetica', 9)
    p.drawString(text_x, y, getattr(settings, 'HOSPITAL_ADDRESS', ''))
    y -= 22
    p.setFont('Helvetica-Bold', 13)
    p.drawString(text_x, y, f"Invoice - {bill.bill_number}")
    y -= 25
    p.setFont('Helvetica', 10)
    p.drawString(50, y, f"Patient: {bill.patient.full_name} ({bill.patient.patient_code})")
    y -= 15
    p.drawString(50, y, f"Date: {bill.created_at:%Y-%m-%d %H:%M}")
    y -= 15
    p.drawString(50, y, f"Payment Method: {bill.get_payment_method_display()}")
    y -= 15
    p.drawString(50, y, f"Bill Type: {bill.get_bill_type_display()}")
    y -= 15
    p.drawString(50, y, f"Payment Status: {bill.get_status_display()}")
    if bill.admission:
        y -= 15
        p.drawString(50, y, f"Department: {bill.admission.department.name}")
        if bill.admission.admitting_doctor:
            y -= 15
            p.drawString(50, y, f"Doctor: Dr. {bill.admission.admitting_doctor.full_name}")
    y -= 30

    p.setFont('Helvetica-Bold', 10)
    p.drawString(50, y, 'Service')
    p.drawString(300, y, 'Qty')
    p.drawString(360, y, 'Unit Price')
    p.drawString(460, y, 'Total')
    y -= 15
    p.setFont('Helvetica', 10)
    for item in bill.items.all():
        p.drawString(50, y, item.service_name[:45])
        p.drawString(300, y, str(item.quantity))
        p.drawString(360, y, f"{item.unit_price}")
        p.drawString(460, y, f"{item.line_total}")
        y -= 15
        if y < 80:
            p.showPage()
            y = height - 60

    y -= 15
    p.setFont('Helvetica-Bold', 12)
    p.drawString(360, y, f"Total: NPR {bill.total_amount}")

    # This invoice's own unique barcode (separate from the Patient QR code).
    if bill.barcode and bill.barcode.storage.exists(bill.barcode.name):
        try:
            barcode_reader = ImageReader(bill.barcode.path)
            p.drawImage(barcode_reader, 50, 40, width=180, height=45, mask='auto', preserveAspectRatio=True)
            p.setFont('Helvetica', 7)
            p.drawString(50, 32, bill.bill_number)
        except Exception:
            pass

    p.setFont('Helvetica-Oblique', 8)
    p.drawCentredString(width / 2, 20, f"This is a computer-generated invoice from {settings.HOSPITAL_NAME}. Thank you.")

    p.showPage()
    p.save()
    buffer.seek(0)

    write_audit_log(
        request, AuditLog.Action.DOCUMENT_DOWNLOADED, f"Invoice PDF downloaded for {bill.bill_number}",
        patient_id_text=bill.patient.patient_code, receipt_number=bill.bill_number,
    )
    return FileResponse(buffer, as_attachment=True, filename=f"{bill.bill_number}.pdf")


@cash_counter_required
def confirm_visit_payment(request, visit_id):
    """
    Cashier physically confirms a walk-in cash payment for an OPD registration visit.
    """
    from patients.models import Visit
    from billing.models import Bill, BillItem, BillType, PaymentMethod
    
    visit = get_object_or_404(Visit, pk=visit_id, payment_status=Visit.PaymentStatus.PENDING)
    
    # Update visit status to Paid
    visit.payment_status = Visit.PaymentStatus.PAID
    visit.save()
    
    # Create an automatic Bill for auditing
    bill = Bill.objects.create(
        patient=visit.patient,
        cashier=request.user,
        bill_type=BillType.OPD,
        payment_method=PaymentMethod.CASH,
        status=Bill.Status.PAID,
    )
    BillItem.objects.create(
        bill=bill,
        service=None,
        service_name=f"OPD Registration Fee ({visit.receipt_number})",
        unit_price=visit.registration_fee,
        quantity=1,
    )
    bill.recalculate_total()
    
    write_audit_log(
        request, AuditLog.Action.PAYMENT,
        f"Confirmed cash payment for visit {visit.receipt_number}",
        patient_id_text=visit.patient.patient_code,
        receipt_number=bill.bill_number,
        amount=visit.registration_fee,
    )
    
    # Trigger notification
    from accounts.utils import create_notification
    from accounts.models import Role
    create_notification(
        title="Payment Completed",
        message=f"Cash payment confirmed for registration visit {visit.receipt_number}.",
        role=Role.REGISTRATION_COUNTER
    )
    
    messages.success(request, f"Payment confirmed for visit {visit.receipt_number}. Receipt generated.")
    return redirect('billing:receipt', pk=bill.pk)
