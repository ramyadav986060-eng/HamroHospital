# Migration Commands

Django migrations are already included in every app's `migrations/` folder,
so on a fresh install you generally only need to **apply** them.

## Apply all migrations (fresh install / after pulling updates)
```powershell
python manage.py migrate
```

## Check for model changes that haven't been turned into a migration yet
```powershell
python manage.py makemigrations --check --dry-run
```

## Create a new migration after changing a model
```powershell
python manage.py makemigrations
python manage.py migrate
```

## Create a migration for one specific app
```powershell
python manage.py makemigrations appointments
python manage.py migrate appointments
```

## See the SQL a migration will run (useful for review before production)
```powershell
python manage.py sqlmigrate appointments 0002
```

## List migration status per app
```powershell
python manage.py showmigrations
```

## Roll back a specific app to an earlier migration
```powershell
python manage.py migrate appointments 0001
```
