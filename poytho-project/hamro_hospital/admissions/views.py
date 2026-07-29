from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.decorators import role_required, super_admin_required
from accounts.models import Role, AuditLog
from accounts.utils import write_audit_log
from admissions.models import Admission, Ward, Bed, DischargeChecklist, AdmissionDeposit, BedTransfer
from admissions.forms import AdmissionForm, DischargeForm, WardForm, BedForm, DischargeChecklistForm, AdmissionDepositForm, BedTransferForm

# Doctors do not admit patients directly; they send Admission Referrals.
admissions_staff_required = role_required(Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER, Role.WARD_ADMISSION, Role.NURSING)


@admissions_staff_required
def admission_list(request):
    import datetime
    from django.utils import timezone
    from consultations.models import Consultation
    from billing.models import Bill
    from django.db.models import Exists, OuterRef, Sum
    
    today = datetime.date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    admissions = Admission.objects.select_related('patient', 'ward', 'bed', 'department').all()
    if not request.GET:
        admissions = admissions.filter(admission_date__gte=timezone.now() - datetime.timedelta(hours=24))
    status = request.GET.get('status', '')
    if status:
        admissions = admissions.filter(status=status)

    date_str = request.GET.get('date', '')
    selected_date = None
    if date_str:
        try:
            selected_date = datetime.date.fromisoformat(date_str)
            admissions = admissions.filter(admission_date__date=selected_date)
        except ValueError:
            selected_date = None

    # Load dynamic inpatient recommendations from consultations (spec section 12)
    from referrals.models import Referral
    admission_referrals = Referral.objects.filter(
        referral_type=Referral.ReferralType.ADMISSION,
        status__in=['new', 'acknowledged', 'in_progress'],
    ).select_related('patient', 'referred_by', 'to_department')
    active_admissions = Admission.objects.filter(patient=OuterRef('visit__patient'), status=Admission.Status.ADMITTED)
    recommended_admissions = Consultation.objects.filter(
        recommend_admission=True
    ).annotate(
        is_already_admitted=Exists(active_admissions)
    ).filter(
        is_already_admitted=False
    ).select_related('visit__patient', 'visit__department', 'doctor')

    currently_admitted = Admission.objects.filter(status=Admission.Status.ADMITTED).select_related('patient', 'ward', 'bed')
    todays_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date=today).aggregate(t=Sum('total_amount'))['t'] or 0
    monthly_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date__gte=month_start).aggregate(t=Sum('total_amount'))['t'] or 0
    yearly_revenue = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID, created_at__date__gte=year_start).aggregate(t=Sum('total_amount'))['t'] or 0
    pending_admissions_count = admission_referrals.count()
    from workflow.models import ServiceOrder
    service_orders = ServiceOrder.objects.filter(service_type=ServiceOrder.ServiceType.ADMISSION).exclude(status=ServiceOrder.Status.COMPLETED).select_related('patient', 'bill')[:10]

    return render(request, 'admissions/admission_list.html', {
        'admissions': admissions, 'statuses': Admission.Status.choices, 'selected_status': status,
        'selected_date': selected_date,
        'todays_count': Admission.objects.filter(admission_date__gte=timezone.now() - datetime.timedelta(hours=24)).count(),
        'monthly_count': Admission.objects.filter(admission_date__date__gte=month_start).count(),
        'yearly_count': Admission.objects.filter(admission_date__date__gte=year_start).count(),
        'currently_admitted_count': currently_admitted.count(),
        'bed_occupancy_count': Bed.objects.filter(is_occupied=True).count(),
        'available_beds_count': Bed.objects.filter(is_occupied=False).count(),
        'pending_admissions_count': pending_admissions_count,
        'todays_revenue': todays_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'recommended_admissions': recommended_admissions,
        'admission_referrals': admission_referrals,
        'service_orders': service_orders,
        'discharge_queue': currently_admitted.order_by('admission_date')[:15],
    })


@admissions_staff_required
def admission_dashboard_details(request):
    import datetime
    from django.db.models import Q, Sum
    from django.utils import timezone
    from billing.models import Bill
    metric = request.GET.get('metric', 'activity')
    admissions = Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor')
    beds = Bed.objects.select_related('ward').all()
    title = 'Admission Details'
    if metric == 'current':
        admissions = admissions.filter(status=Admission.Status.ADMITTED)
        title = 'Current Admitted Patients'
    elif metric == 'occupied_beds':
        beds = beds.filter(is_occupied=True)
        title = 'Bed Occupancy'
    elif metric == 'available_beds':
        beds = beds.filter(is_occupied=False)
        title = 'Available Beds'
    elif metric == 'revenue':
        admissions = admissions.none()
        title = 'Admission Revenue Records'
    else:
        admissions = admissions.filter(admission_date__gte=timezone.now() - datetime.timedelta(hours=24))
        title = 'Admission Activity - Latest 24 Hours'

    q = (request.GET.get('q') or '').strip()
    date_filter = request.GET.get('date_filter', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    today = timezone.localdate()
    if q:
        admissions = admissions.filter(Q(patient__patient_code__icontains=q) | Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q) | Q(patient__phone_number__icontains=q) | Q(admission_number__icontains=q) | Q(ward__name__icontains=q) | Q(bed__bed_number__icontains=q))
        beds = beds.filter(Q(ward__name__icontains=q) | Q(bed_number__icontains=q))
    if date_filter or start_date or end_date:
        if date_filter == 'today': admissions = admissions.filter(admission_date__date=today)
        elif date_filter == 'week': admissions = admissions.filter(admission_date__date__gte=today - datetime.timedelta(days=today.weekday()))
        elif date_filter == 'month': admissions = admissions.filter(admission_date__date__gte=today.replace(day=1))
        elif date_filter == 'year': admissions = admissions.filter(admission_date__date__gte=today.replace(month=1, day=1))
        elif date_filter == 'all': pass
        try:
            if start_date: admissions = admissions.filter(admission_date__date__gte=datetime.date.fromisoformat(start_date))
            if end_date: admissions = admissions.filter(admission_date__date__lte=datetime.date.fromisoformat(end_date))
        except ValueError:
            pass
    revenue_bills = Bill.objects.filter(bill_type='ipd', status=Bill.Status.PAID).select_related('patient')
    if metric == 'revenue':
        if date_filter == 'today': revenue_bills = revenue_bills.filter(created_at__date=today)
        elif date_filter == 'week': revenue_bills = revenue_bills.filter(created_at__date__gte=today - datetime.timedelta(days=today.weekday()))
        elif date_filter == 'month' or not request.GET.get('date_filter'): revenue_bills = revenue_bills.filter(created_at__date__gte=today.replace(day=1))
        elif date_filter == 'year': revenue_bills = revenue_bills.filter(created_at__date__gte=today.replace(month=1, day=1))
        try:
            if start_date: revenue_bills = revenue_bills.filter(created_at__date__gte=datetime.date.fromisoformat(start_date))
            if end_date: revenue_bills = revenue_bills.filter(created_at__date__lte=datetime.date.fromisoformat(end_date))
        except ValueError: pass
        if q:
            revenue_bills = revenue_bills.filter(Q(bill_number__icontains=q) | Q(patient__patient_code__icontains=q) | Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q))
    return render(request, 'admissions/dashboard_details.html', {
        'title': title, 'metric': metric, 'admissions': admissions.order_by('-admission_date')[:1000],
        'beds': beds, 'revenue_bills': revenue_bills.order_by('-created_at')[:1000],
        'revenue_total': revenue_bills.aggregate(t=Sum('total_amount'))['t'] or 0,
        'q': q, 'date_filter': date_filter, 'start_date': start_date, 'end_date': end_date,
    })


@admissions_staff_required
def search_patient(request):
    from django.db.models import Q
    from patients.models import Patient
    q = request.GET.get('q', '')
    patients = Patient.objects.none()
    if q:
        patients = Patient.objects.filter(
            Q(patient_code__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(phone_number__icontains=q)
        ).distinct()
    return render(request, 'admissions/search_patient.html', {'q': q, 'patients': patients})


@admissions_staff_required
def admit_patient(request, patient_id):
    from patients.models import Patient
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.patient = patient
            admission.created_by = request.user
            admission.save()
            if form.cleaned_data.get('admission_datetime'):
                admission.admission_date = form.cleaned_data['admission_datetime']
                admission.save(update_fields=['admission_date'])
            if form.cleaned_data.get('notes'):
                admission.reason_for_admission = f"{admission.reason_for_admission} | Notes: {form.cleaned_data['notes']}"
                admission.save(update_fields=['reason_for_admission'])
            write_audit_log(
                request, AuditLog.Action.ADMISSION,
                f"Admitted {patient.full_name} to {admission.ward.name}",
                patient_id_text=patient.patient_code, receipt_number=admission.admission_number,
            )
            messages.success(request, f'{patient.full_name} admitted. Admission #: {admission.admission_number}')
            return redirect('admissions:admission_detail', pk=admission.pk)
    else:
        initial = {}
        referral_id = request.GET.get('referral')
        if referral_id:
            from referrals.models import Referral
            referral = Referral.objects.filter(pk=referral_id, patient=patient).first()
            if referral:
                initial = {
                    'department': referral.to_department_id,
                    'reason_for_admission': referral.reason,
                    'diagnosis': referral.diagnosis,
                }
        form = AdmissionForm(initial=initial)
    return render(request, 'admissions/admit_form.html', {'form': form, 'patient': patient})


@admissions_staff_required
def admission_detail(request, pk):
    admission = get_object_or_404(
        Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor'), pk=pk,
    )
    checklist, _ = DischargeChecklist.objects.get_or_create(admission=admission)
    # Auto-set bill clearance when there are no pending bills.
    from billing.models import Bill
    no_pending_bills = not Bill.objects.filter(patient=admission.patient, status=Bill.Status.PENDING).exists()
    if checklist.all_bills_paid != no_pending_bills:
        checklist.all_bills_paid = no_pending_bills
        checklist.save(update_fields=['all_bills_paid', 'updated_at'])
    discharge_form = DischargeForm() if admission.status == Admission.Status.ADMITTED else None
    checklist_form = DischargeChecklistForm(instance=checklist) if admission.status == Admission.Status.ADMITTED else None
    deposits = admission.deposits.select_related('received_by').all()
    transfers = admission.bed_transfers.select_related('from_ward', 'from_bed', 'to_ward', 'to_bed', 'transferred_by').all()
    return render(request, 'admissions/admission_detail.html', {
        'admission': admission, 'discharge_form': discharge_form, 'checklist': checklist, 'checklist_form': checklist_form,
        'deposits': deposits, 'transfers': transfers,
    })


@admissions_staff_required
def admission_slip(request, pk):
    """Printable Admission Slip - same unified print identity as every other document."""
    admission = get_object_or_404(
        Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor'), pk=pk,
    )
    return render(request, 'admissions/admission_slip.html', {'admission': admission})


@admissions_staff_required
def admission_deposit_create(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        form = AdmissionDepositForm(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.admission = admission
            deposit.received_by = request.user
            deposit.save()
            from workflow.models import PatientTimeline
            from workflow.utils import add_timeline
            add_timeline(admission.patient, PatientTimeline.EventType.PAYMENT, f'Admission {deposit.get_deposit_type_display()}', f'NPR {deposit.amount}', actor=request.user, related_url=reverse('admissions:admission_deposit_receipt', args=[deposit.pk]), source=deposit)
            messages.success(request, 'Admission deposit record saved.')
            return redirect('admissions:admission_deposit_receipt', pk=deposit.pk)
    else:
        form = AdmissionDepositForm()
    return render(request, 'admissions/deposit_form.html', {'form': form, 'admission': admission})


@admissions_staff_required
def admission_deposit_receipt(request, pk):
    deposit = get_object_or_404(AdmissionDeposit.objects.select_related('admission__patient', 'received_by'), pk=pk)
    receipt = {
        'title': 'Admission Deposit Receipt', 'number': deposit.receipt_number or f'DEP-{deposit.pk:06d}',
        'patient': deposit.admission.patient, 'department': 'Admission',
        'service_name': deposit.get_deposit_type_display(), 'amount': deposit.amount,
        'payment_status': 'Recorded', 'payment_method': deposit.payment_method,
        'printed_by': deposit.received_by, 'barcode_url': deposit.admission.barcode.url if deposit.admission.barcode else '',
    }
    return render(request, 'admissions/deposit_receipt.html', {'deposit': deposit, 'receipt': receipt})


@admissions_staff_required
def admission_transfer_bed(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        form = BedTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.admission = admission
            transfer.transferred_by = request.user
            transfer.save()
            from workflow.models import PatientTimeline
            from workflow.utils import add_timeline
            add_timeline(admission.patient, PatientTimeline.EventType.ADMISSION, 'Bed transfer', f'{transfer.from_ward} / {transfer.from_bed} → {transfer.to_ward} / {transfer.to_bed}', actor=request.user, related_url=reverse('admissions:admission_detail', args=[admission.pk]), source=transfer)
            messages.success(request, 'Bed transfer completed.')
            return redirect('admissions:admission_detail', pk=admission.pk)
    else:
        form = BedTransferForm(initial={'to_ward': admission.ward_id})
    return render(request, 'admissions/bed_transfer_form.html', {'form': form, 'admission': admission})


@admissions_staff_required
def update_discharge_checklist(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    checklist, _ = DischargeChecklist.objects.get_or_create(admission=admission)
    if request.method == 'POST':
        form = DischargeChecklistForm(request.POST, instance=checklist)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            messages.success(request, 'Discharge checklist updated.')
    return redirect('admissions:admission_detail', pk=admission.pk)


@admissions_staff_required
def discharge_patient(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        from billing.models import Bill
        pending_bills = Bill.objects.filter(patient=admission.patient, status=Bill.Status.PENDING)
        checklist, _ = DischargeChecklist.objects.get_or_create(admission=admission)
        if pending_bills.exists():
            messages.error(request, 'Cannot discharge: patient has pending payments. Please clear all bills first.')
            return redirect('admissions:admission_detail', pk=admission.pk)
        if not checklist.is_complete:
            messages.error(request, 'Cannot discharge: discharge checklist is incomplete.')
            return redirect('admissions:admission_detail', pk=admission.pk)
        form = DischargeForm(request.POST)
        if form.is_valid():
            admission.discharge(
                condition=form.cleaned_data['discharge_condition'],
                summary=form.cleaned_data['discharge_summary'],
                follow_up_instructions=form.cleaned_data['follow_up_instructions'],
                procedures_performed=form.cleaned_data.get('procedures_performed',''),
                medicines_on_discharge=form.cleaned_data.get('medicines_on_discharge',''),
                diet_advice=form.cleaned_data.get('diet_advice',''),
                activity_recommendations=form.cleaned_data.get('activity_recommendations',''),
                emergency_instructions=form.cleaned_data.get('emergency_instructions',''),
                follow_up_date=form.cleaned_data.get('follow_up_date'),
                follow_up_department=form.cleaned_data.get('follow_up_department'),
                follow_up_doctor=form.cleaned_data.get('follow_up_doctor'),
                recommended_investigations=form.cleaned_data.get('recommended_investigations',''),
                follow_up_additional_notes=form.cleaned_data.get('follow_up_additional_notes',''),
            )
            write_audit_log(
                request, AuditLog.Action.DISCHARGE,
                f"Discharged {admission.patient.full_name} ({admission.get_discharge_condition_display()})",
                patient_id_text=admission.patient.patient_code, receipt_number=admission.admission_number,
            )
            messages.success(request, f'{admission.patient.full_name} discharged. Bed freed.')
            return redirect('admissions:admission_detail', pk=admission.pk)
    return redirect('admissions:admission_detail', pk=admission.pk)


# --- Ward / Bed management (Super Admin only) -------------------------------

@admissions_staff_required
def ward_list(request):
    wards = Ward.objects.prefetch_related('beds').all()
    return render(request, 'admissions/ward_list.html', {'wards': wards})


@super_admin_required
def ward_create(request):
    if request.method == 'POST':
        form = WardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ward created.')
            return redirect('admissions:ward_list')
    else:
        form = WardForm()
    return render(request, 'admissions/ward_form.html', {'form': form, 'title': 'Add Ward'})


@super_admin_required
def bed_create(request):
    if request.method == 'POST':
        form = BedForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bed added.')
            return redirect('admissions:ward_list')
    else:
        form = BedForm()
    return render(request, 'admissions/bed_form.html', {'form': form, 'title': 'Add Bed'})


@admissions_staff_required
def discharge_package_pdf(request, pk):
    """Generate a final discharge package PDF for the admission.

    Includes admission summary, discharge checklist, deposits, bills and key
    document counts. This is intentionally generated on demand so old records
    remain unchanged and no background job is required for the first version.
    """
    from io import BytesIO
    from django.http import HttpResponse
    from billing.models import Bill
    from documents.models import PatientDocument
    from workflow.models import PatientTimeline
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

    admission = get_object_or_404(Admission.objects.select_related('patient', 'ward', 'bed', 'department', 'admitting_doctor'), pk=pk)
    checklist, _ = DischargeChecklist.objects.get_or_create(admission=admission)
    bills = Bill.objects.filter(patient=admission.patient).order_by('-created_at')
    deposits = admission.deposits.all()
    documents = PatientDocument.objects.filter(patient=admission.patient, is_active=True)
    timeline = PatientTimeline.objects.filter(patient=admission.patient)[:20]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=.55*inch, rightMargin=.55*inch, topMargin=.55*inch, bottomMargin=.55*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8, leading=10))
    story = []
    from accounts.models import HospitalSetting
    setting = HospitalSetting.get_solo()
    if getattr(setting, 'logo', None):
        try:
            story.append(Image(setting.logo.path, width=.65*inch, height=.65*inch))
        except Exception:
            pass
    story.append(Paragraph(setting.name, styles['Title']))
    story.append(Paragraph(f"{setting.address} | {setting.phone} | {setting.email}", styles['Small']))
    story.append(Paragraph('Professional Discharge Summary & Package', styles['Heading2']))
    story.append(Paragraph(f"Admission: {admission.admission_number} | Patient: {admission.patient.patient_code}", styles['Small']))
    if admission.barcode:
        try:
            story.append(Image(admission.barcode.path, width=1.8*inch, height=.42*inch))
        except Exception:
            pass
    story.append(Spacer(1, 8))

    patient_rows = [
        ['Patient', admission.patient.full_name],
        ['Patient ID', admission.patient.patient_code],
        ['Phone', admission.patient.phone_number],
        ['Department', admission.department.name],
        ['Ward / Bed', f"{admission.ward.name} / {admission.bed.bed_number if admission.bed else '-'}"],
        ['Admitted', admission.admission_date.strftime('%Y-%m-%d %H:%M')],
        ['Discharged', admission.discharge_date.strftime('%Y-%m-%d %H:%M') if admission.discharge_date else 'Not discharged yet'],
        ['Status', admission.get_status_display()],
        ['Final Diagnosis', admission.diagnosis or '-'],
        ['Treating Doctor', f"Dr. {admission.admitting_doctor.full_name}" if admission.admitting_doctor else '-'],
    ]
    story.append(_pdf_table(patient_rows))
    story.append(Spacer(1, 10))
    story.append(Paragraph('Discharge Checklist', styles['Heading2']))
    checklist_rows = [[name.replace('_', ' ').title(), 'Yes' if getattr(checklist, name) else 'No'] for name in [
        'all_bills_paid', 'lab_reports_complete', 'radiology_reports_complete', 'medicine_charges_complete',
        'discharge_summary_prepared', 'nursing_clearance', 'insurance_clearance', 'bed_release_ready'
    ]]
    story.append(_pdf_table(checklist_rows))
    story.append(Spacer(1, 10))
    story.append(Paragraph('Treatment / Discharge Summary', styles['Heading2']))
    story.append(_pdf_table([['Treatment Summary', admission.discharge_summary or '-'], ['Procedures Performed', admission.procedures_performed or '-'], ['Medicines on Discharge', admission.medicines_on_discharge or '-'], ['Diet Advice', admission.diet_advice or '-'], ['Activity Recommendations', admission.activity_recommendations or '-'], ['Emergency Instructions', admission.emergency_instructions or '-']]))
    story.append(Spacer(1, 10))
    story.append(Paragraph('Follow-up Information', styles['Heading2']))
    story.append(_pdf_table([['Follow-up Date', admission.follow_up_date or '-'], ['Follow-up Department', admission.follow_up_department.name if admission.follow_up_department else '-'], ['Follow-up Doctor', f"Dr. {admission.follow_up_doctor.full_name}" if admission.follow_up_doctor else '-'], ['Follow-up Instructions', admission.follow_up_instructions or '-'], ['Recommended Investigations', admission.recommended_investigations or '-'], ['Additional Notes', admission.follow_up_additional_notes or '-']]))
    story.append(Spacer(1, 10))

    story.append(Paragraph('Financial Summary / Discharge Billing', styles['Heading2']))
    bill_total = sum((b.total_amount for b in bills), start=0)
    paid_total = sum((b.total_amount for b in bills if b.status == Bill.Status.PAID), start=0)
    pending_total = sum((b.total_amount for b in bills if b.status == Bill.Status.PENDING), start=0)
    deposit_total = sum((d.amount for d in deposits if d.deposit_type == 'deposit'), start=0)
    story.append(_pdf_table([
        ['Total Bills', f'NPR {bill_total}'], ['Paid Bills', f'NPR {paid_total}'],
        ['Pending Bills', f'NPR {pending_total}'], ['Deposits', f'NPR {deposit_total}'],
    ]))
    story.append(Spacer(1, 10))

    story.append(Paragraph('Recent Bills', styles['Heading2']))
    bill_rows = [['Bill #', 'Date', 'Status', 'Amount']] + [[b.bill_number, b.created_at.strftime('%Y-%m-%d'), b.get_status_display(), f'NPR {b.total_amount}'] for b in bills[:10]]
    story.append(_pdf_table(bill_rows, header=True))
    story.append(Spacer(1, 10))

    story.append(Paragraph('Documents and Recent Timeline', styles['Heading2']))
    story.append(Paragraph(f"Documents on file: {documents.count()}", styles['BodyText']))
    timeline_rows = [['Date', 'Type', 'Event']] + [[e.event_at.strftime('%Y-%m-%d %H:%M'), e.get_event_type_display(), e.title] for e in timeline]
    story.append(_pdf_table(timeline_rows, header=True))
    story.append(Spacer(1, 12))
    story.append(Spacer(1, 18))
    story.append(_pdf_table([['Doctor Signature', '________________________'], ['Hospital Stamp', '________________________'], ['Authorized Signature', '________________________']]))
    story.append(Paragraph('This package is computer generated by Hamro Hospital HIS.', styles['Small']))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{admission.admission_number}-discharge-package.pdf"'
    return response


def _pdf_table(rows, header=False):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    t = Table(rows, repeatRows=1 if header else 0)
    style = [
        ('GRID', (0,0), (-1,-1), .25, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 4), ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]
    if header:
        style += [('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DBEAFE')), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')]
    t.setStyle(TableStyle(style))
    return t
