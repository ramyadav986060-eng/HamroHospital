# Requirements

## System requirements
- **OS:** Windows 10/11, macOS, or Linux — all tested
- **Python:** 3.11 or 3.12 (Django 5.0 requires 3.10+)
- **RAM:** 2 GB minimum, 4 GB recommended for running `seed_all` at full scale
- **Disk space:** ~500 MB for code + dependencies, plus ~150 MB once the
  full demo dataset (QR codes, barcodes, generated PDFs) has been seeded

## Python package requirements (`requirements.txt`)
| Package | Purpose |
|---|---|
| Django >=5.0,<5.1 | Web framework |
| django-jazzmin >=3.0 | Admin UI theme |
| Pillow >=10.0 | Image handling (photos, QR/barcode composition) |
| qrcode >=7.4 | Patient QR code generation |
| python-barcode >=0.15 | Billing/pharmacy/lab/admission barcode generation |
| reportlab >=4.0 | PDF invoice/report generation |
| python-dotenv >=1.0 | `.env` configuration loading |
| requests >=2.31 | eSewa payment gateway calls |
| openpyxl >=3.1 | Excel export for reports |

Install all of them with:
```
pip install -r requirements.txt
```

## Database
- **Default:** SQLite (zero configuration, ships ready to run)
- **Supported:** Any database Django supports (PostgreSQL, MySQL) by editing
  `config/settings.py` — see `03_Database_Setup.md`
