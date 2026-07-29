# SQLite to PostgreSQL migration

## Development default
`DJANGO_DB_ENGINE=sqlite` is the default. `db.sqlite3` remains the normal VS Code development database. No PostgreSQL server is required to run the project.

## Switch safely without losing data
1. Keep a backup of `db.sqlite3`.
2. While SQLite is selected, export portable fixture data (excluding Django content types and permissions):
   ```powershell
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 2 > hms-data.json
   ```
3. Create an empty PostgreSQL database and set `DJANGO_DB_ENGINE=postgres` plus the `POSTGRES_*` values from `.env.example` in your local `.env`.
4. Install dependencies, then create the same schema and load the export:
   ```powershell
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py loaddata hms-data.json
   python manage.py check
   ```
5. Verify the application, then retain both the SQLite file and fixture backup until PostgreSQL is accepted.

All installed applications use Django migrations, so the same migrations run on SQLite and PostgreSQL. Do not run `migrate` against PostgreSQL before setting its credentials.
