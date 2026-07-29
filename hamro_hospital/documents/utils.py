from io import BytesIO

from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from documents.models import PatientDocument, DocumentCategory


def _pdf_bytes(title, patient, rows, body=''):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 0.6 * inch
    p.setFont('Helvetica-Bold', 15)
    p.drawString(0.7 * inch, y, 'Hamro Hospital')
    y -= 18
    p.setFont('Helvetica-Bold', 12)
    p.drawString(0.7 * inch, y, title[:90])
    y -= 18
    p.setFont('Helvetica', 9)
    p.drawString(0.7 * inch, y, f'Patient: {patient.full_name} | ID: {patient.patient_code} | Phone: {patient.phone_number}')
    y -= 18
    p.drawString(0.7 * inch, y, f'Generated: {timezone.localtime(timezone.now()):%Y-%m-%d %H:%M}')
    y -= 16
    p.line(0.7 * inch, y, width - 0.7 * inch, y)
    y -= 18
    for label, value in rows:
        if y < 1.0 * inch:
            p.showPage(); y = height - 0.7 * inch; p.setFont('Helvetica', 9)
        p.setFont('Helvetica-Bold', 9); p.drawString(0.7 * inch, y, str(label)[:32])
        p.setFont('Helvetica', 9); p.drawString(2.3 * inch, y, str(value or '-')[:95])
        y -= 15
    if body:
        y -= 8
        p.setFont('Helvetica-Bold', 10); p.drawString(0.7 * inch, y, 'Details')
        y -= 15
        p.setFont('Helvetica', 9)
        for line in str(body).splitlines() or [body]:
            if y < 1.0 * inch:
                p.showPage(); y = height - 0.7 * inch; p.setFont('Helvetica', 9)
            p.drawString(0.7 * inch, y, line[:110])
            y -= 13
    y = max(y - 20, 0.8 * inch)
    p.line(0.7 * inch, y, 2.6 * inch, y); p.drawString(0.7 * inch, y - 12, 'Authorized Signature')
    p.showPage(); p.save(); buffer.seek(0)
    return buffer.getvalue()


def add_medical_history_document(patient, *, category=DocumentCategory.OTHER, title, department_note='', remarks='', uploaded_by=None, rows=None, body='', source_key=''):
    if not patient:
        return None
    source_key = source_key or title
    if PatientDocument.objects.filter(patient=patient, title=title, remarks__icontains=f'[auto:{source_key}]').exists():
        return None
    rows = rows or []
    pdf = _pdf_bytes(title, patient, rows, body)
    doc = PatientDocument(
        patient=patient, category=category, title=title, department_note=department_note,
        remarks=f'{remarks}\n[auto:{source_key}]'.strip(), uploaded_by=uploaded_by,
        uploaded_by_role=getattr(uploaded_by, 'role', '') if uploaded_by else '',
    )
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in title)[:70]
    doc.file.save(f'{safe}.pdf', ContentFile(pdf), save=True)
    return doc
