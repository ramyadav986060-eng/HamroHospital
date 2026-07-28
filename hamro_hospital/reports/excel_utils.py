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
