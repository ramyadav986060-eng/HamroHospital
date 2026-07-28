from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font


def export_rows_to_excel(headers, rows, filename, sheet_title='Report'):
    """
    Generic 'headers + rows' -> downloadable .xlsx response.
    headers: list of column titles
    rows: list of tuples/lists, one per row, matching headers order
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # Excel sheet-name length limit

    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append(list(row))

    for col_cells in ws.columns:
        length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 2, 10), 40)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response



def export_rows_to_pdf(headers, rows, filename, title='Report', subtitle=''):
    """Generic report PDF export with hospital-style heading and table."""
    from io import BytesIO
    from django.http import HttpResponse
    from django.utils import timezone
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    page_size = landscape(A4) if len(headers) > 5 else A4
    doc = SimpleDocTemplate(buffer, pagesize=page_size, leftMargin=.45*inch, rightMargin=.45*inch, topMargin=.5*inch, bottomMargin=.5*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallCell', parent=styles['BodyText'], fontSize=7, leading=8.5))
    story = [Paragraph('Hamro Hospital', styles['Title']), Paragraph(title, styles['Heading2'])]
    if subtitle:
        story.append(Paragraph(subtitle, styles['Normal']))
    story.append(Paragraph(f'Generated: {timezone.now():%Y-%m-%d %H:%M}', styles['Normal']))
    story.append(Spacer(1, 8))

    def cell(value):
        return Paragraph(str(value if value is not None else ''), styles['SmallCell'])

    data = [[cell(h) for h in headers]] + [[cell(v) for v in row] for row in rows]
    usable_width = page_size[0] - doc.leftMargin - doc.rightMargin
    col_width = usable_width / max(1, len(headers))
    table = Table(data, colWidths=[col_width] * len(headers), repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DBEAFE')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), .25, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
