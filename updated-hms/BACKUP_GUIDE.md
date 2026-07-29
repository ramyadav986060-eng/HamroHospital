# Backup and Restore Guide

## Manual backup

Use the built-in command:

```bash
python manage.py backup_data
```

Backups are stored in the project backup folder when configured.

## Restore

Use restore carefully on a maintenance window:

```bash
python manage.py restore_data path/to/backup.json
```

## Recommended production backup

- Daily PostgreSQL dump.
- Daily media folder backup.
- Weekly full server snapshot.
- Offsite/cloud copy.
- Monthly restore drill.

## Final backup artifact

A final backup copy is included:

```text
backups/hamro_hospital_final_backup.zip
```
