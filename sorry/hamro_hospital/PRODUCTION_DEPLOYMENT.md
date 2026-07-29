# Hamro Hospital Production Deployment Notes

This project now includes the production foundations for WebSockets, Celery background jobs, eSewa payments, and the central HIS workflow engine.

## Required environment variables

```env
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=change-this-long-random-secret

# Redis is required in production for WebSockets and Celery.
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1

# eSewa live credentials
ESEWA_SANDBOX=False
ESEWA_MERCHANT_CODE=your_live_merchant_code
ESEWA_SECRET_KEY=your_live_secret_key

# Email/SMS
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=Hamro Hospital <your_email>
```

## Run services

### ASGI application
Use Daphne/Uvicorn for WebSockets:

```bash
daphne config.asgi:application
```

### Celery worker

```bash
celery -A config worker -l info
```

### Celery beat, if scheduled tasks are enabled

```bash
celery -A config beat -l info
```

## Health checks

Run before deployment:

```bash
python manage.py check
python manage.py migrate
python manage.py test workflow
python manage.py verify_production_config
```

## Notes

- Redis is mandatory for production WebSocket notifications. In-memory channels are only for local development.
- eSewa live mode must never use `EPAYTEST` credentials.
- Celery must run separately from the web server.
- Backups and daily reports should be scheduled through Celery Beat or cron.
