# Database Setup

## Default: SQLite (recommended for demo/evaluation)
No setup required. `config/settings.py` already points to:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
The file `db.sqlite3` is created automatically the first time you run
`python manage.py migrate`.

## Switching to PostgreSQL (recommended for a real production deployment)
1. Install the driver: `pip install psycopg2-binary`
2. Create a database and user in PostgreSQL.
3. Replace the `DATABASES` block in `config/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tu_hospital',
        'USER': 'tu_hospital_user',
        'PASSWORD': 'change-me',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```
4. Run `python manage.py migrate` again against the new database.
5. Re-run `python manage.py seed_all` to populate it.

## Switching to MySQL
1. Install the driver: `pip install mysqlclient`
2. Use `django.db.backends.mysql` as the engine with the equivalent
   NAME/USER/PASSWORD/HOST/PORT values.

## Backing up and restoring
See the built-in management commands (already usable with SQLite or any
other backend Django supports):
```powershell
python manage.py backup_data
python manage.py restore_data backups\tuh_backup_20260101_120000.json --yes
```
Full command reference is in `PowerShell Commands.txt`.
