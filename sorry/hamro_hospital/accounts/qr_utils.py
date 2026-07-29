"""
Shared QR-code / barcode generation helpers.

Every module (billing, pharmacy, laboratory, admissions, insurance, ...)
gets its own unique code on its own record, separate from the Patient's
QR code (patients.models.Patient._generate_qr_code, left untouched).

Two styles are available:
- generate_qr_file(data)      -> classic square QR code (django ContentFile)
- generate_barcode_file(data) -> modern rectangular Code128 barcode (ContentFile)

Usage inside a model's save():

    from accounts.qr_utils import generate_barcode_file

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            self.barcode.save(f"{self.invoice_number}.png",
                               generate_barcode_file(self.invoice_number), save=False)
            MyModel.objects.filter(pk=self.pk).update(barcode=self.barcode.name)
"""
import io


def generate_qr_file(data):
    """Square QR code. Returns a django ContentFile (PNG)."""
    import qrcode
    from django.core.files.base import ContentFile

    qr_img = qrcode.make(data)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())


def generate_barcode_file(data):
    """
    Modern rectangular Code128 barcode. Returns a django ContentFile (PNG).
    Falls back to a square QR code if the `python-barcode` package isn't
    installed, so nothing breaks if requirements.txt hasn't been re-installed yet.
    """
    from django.core.files.base import ContentFile

    try:
        import barcode
        from barcode.writer import ImageWriter

        code128 = barcode.get('code128', str(data), writer=ImageWriter())
        buffer = io.BytesIO()
        code128.write(buffer, options={
            'module_height': 10.0,
            'font_size': 8,
            'text_distance': 3,
            'quiet_zone': 2,
        })
        return ContentFile(buffer.getvalue())
    except ImportError:
        return generate_qr_file(data)
