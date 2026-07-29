# Common Error Fixes

### `ModuleNotFoundError: No module named 'django'` (or any other package)
Your virtual environment isn't activated, or dependencies aren't installed.
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### `error: externally-managed-environment` when running `pip install`
Some Linux/macOS Python installs block global pip installs. Either use a
virtual environment (recommended, see Installation Guide), or add the flag:
```bash
pip install -r requirements.txt --break-system-packages
```

### `django.db.utils.OperationalError: no such table: ...`
Migrations haven't been applied yet.
```powershell
python manage.py migrate
```

### `That port is already in use`
Another process (often a previous `runserver`) is still bound to port 8000.
```powershell
python manage.py runserver 8001
```
or find and stop the other process.

### `seed_all` seems to "hang" or your terminal times out partway through
It isn't hanging — generating thousands of QR codes/barcodes takes a few
minutes. If your environment has a hard command timeout, seed in stages
instead (see `05_Seeding_Commands.md`). Because the command tops up rather
than duplicates, it is always safe to just run it again.

### `IntegrityError: UNIQUE constraint failed: appointments_appointment.appointment_number`
This was a bug in earlier versions where a blank `appointment_number` on
two different *unpaid* bookings collided under the unique constraint. It
is fixed in this version (the field is now nullable, and a
number is only assigned once the booking is actually paid). If you still
see this on old data, run `python manage.py migrate appointments` to make
sure migration `0002_alter_appointment_appointment_number` has been applied.

### Static files (CSS/logo) don't load after deploying with `DEBUG = False`
Run:
```powershell
python manage.py collectstatic --noinput
```
and make sure your web server (nginx/IIS/etc.) is configured to serve the
`STATIC_ROOT` folder, or use a package like `whitenoise` for a simple setup.

### QR codes / barcodes are missing on new records
Make sure `Pillow`, `qrcode`, and `python-barcode` installed correctly —
re-run `pip install -r requirements.txt` and check for errors in the output.

### eSewa payment redirect doesn't work locally
The eSewa integration points at eSewa's sandbox/UAT endpoint by default,
which requires your `success_url`/`failure_url` to be reachable from the
internet (not `127.0.0.1`). For local development, either use a tunneling
tool (e.g. ngrok) or just test the booking flow up to the "Continue to
eSewa Payment" step - the rest of the flow (receipt, QR) can be exercised
by marking an appointment paid directly, e.g. via the Django shell or by
letting `seed_all` generate paid demo appointments for you.

### `createsuperuser` fails / already have an account
Use one of the built-in demo accounts instead — see
`07_Admin_Login_And_Demo_Accounts.md` — or delete the conflicting username
first via `python manage.py shell`.

### Migration conflicts after pulling updates
```powershell
python manage.py makemigrations --merge
python manage.py migrate
```
