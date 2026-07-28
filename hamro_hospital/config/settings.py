"""
Django settings for the Hamro Hospital Management System (Nepal).

This is Checkpoint 1 of the multi-part build:
    accounts, website, departments, doctors, patients

Later checkpoints add: appointments, consultations, laboratory, radiology,
admissions, billing, pharmacy, insurance, reports.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-key-change-this-in-production-tuh-2026'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*'] if DEBUG else os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Hamro Hospital Management System apps (Checkpoint 1)
    'accounts',
    'website',
    'departments',
    'doctors',
    'patients',
    'appointments',
    'consultations',
    'laboratory',
    'radiology',
    'admissions',
    'billing',
    'pharmacy',
    'insurance',
    'reports',
    'patient_portal',

    # Checkpoint 3 additions
    'documents',
    'nursing',
    'operation_theatre',
    'blood_bank',
    'finance',
    'referrals',
    'medical_records',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.hospital_settings',
                'patient_portal.context_processors.portal_patient_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database
# SQLite remains the default for VS Code development.  Set DJANGO_DB_ENGINE=postgres
# (and the POSTGRES_* variables in .env) to run the same migrations on PostgreSQL.
# Do not switch an existing SQLite file in place: use the documented dump/load
# migration procedure so data is preserved.
# ---------------------------------------------------------------------------
DB_ENGINE = os.environ.get('DJANGO_DB_ENGINE', 'sqlite').lower()
if DB_ENGINE in {'postgres', 'postgresql'}:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'tuhospital'),
            'USER': os.environ.get('POSTGRES_USER', 'tuhospital'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            # Persistent connections reduce connection setup overhead in production.
            'CONN_MAX_AGE': int(os.environ.get('POSTGRES_CONN_MAX_AGE', '60')),
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('MYSQL_DB', 'tuhospital'),
            'USER': os.environ.get('MYSQL_USER', 'tuhospital'),
            'PASSWORD': os.environ.get('MYSQL_PASSWORD', ''),
            'HOST': os.environ.get('MYSQL_HOST', '127.0.0.1'),
            'PORT': os.environ.get('MYSQL_PORT', '3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }
elif DB_ENGINE == 'sqlite':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    raise ValueError("DJANGO_DB_ENGINE must be 'sqlite' or 'postgres'.")

# ---------------------------------------------------------------------------
# Custom user model & auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:post_login_redirect'
LOGOUT_REDIRECT_URL = 'website:home'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Hospital-specific settings
# ---------------------------------------------------------------------------
HOSPITAL_NAME = os.environ.get('HOSPITAL_NAME', 'Hamro Hospital')
HOSPITAL_CODE = os.environ.get('HOSPITAL_CODE', 'HT')  # used in Patient IDs: HT-2026-000001
HOSPITAL_EMERGENCY_PHONE = os.environ.get('HOSPITAL_EMERGENCY_PHONE', '01-4412303')
HOSPITAL_EMAIL = os.environ.get('HOSPITAL_EMAIL', 'info@hamrohospital.example.np')

# --- Email (Patient Portal "Forgot Password" - Email Reset) ------------------
# Defaults to Django's console backend so reset emails actually go out and are
# visible (printed to the runserver log) with zero setup - the same "works
# now, production is just env vars" pattern used for the database config.
# Set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend plus the
# EMAIL_HOST_* vars below to send real emails in production.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', HOSPITAL_EMAIL)
HOSPITAL_ADDRESS = os.environ.get('HOSPITAL_ADDRESS', 'Maharajgunj, Kathmandu, Nepal')

# Registration fees (NPR) - used by patients app; kept configurable, not hardcoded in templates
NEW_PATIENT_REGISTRATION_FEE = 100
OLD_PATIENT_REGISTRATION_FEE = 50

# eSewa (used starting Checkpoint 2 - appointments app); placeholders here for future wiring
ESEWA_MERCHANT_CODE = os.environ.get('ESEWA_MERCHANT_CODE', 'EPAYTEST')
ESEWA_SECRET_KEY = os.environ.get('ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')
ESEWA_SANDBOX = os.environ.get('ESEWA_SANDBOX', 'True') == 'True'

# ---------------------------------------------------------------------------
# Messages (Bootstrap alert classes)
# ---------------------------------------------------------------------------
from django.contrib.messages import constants as messages_constants
MESSAGE_TAGS = {
    messages_constants.DEBUG: 'secondary',
    messages_constants.INFO: 'info',
    messages_constants.SUCCESS: 'success',
    messages_constants.WARNING: 'warning',
    messages_constants.ERROR: 'danger',
}

# ---------------------------------------------------------------------------
# Jazzmin - modern Django Admin theme (sidebar nav, icons, dark mode, better
# forms/tables/search). All master/catalogue data (medicines, lab tests,
# radiology tests, operations, billing services, districts, etc.) lives in
# Django Admin per the spec, so a clean, navigable admin matters here.
# ---------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    'site_title': f'{HOSPITAL_NAME} Admin',
    'site_header': HOSPITAL_NAME,
    'site_brand': HOSPITAL_NAME,
    'welcome_sign': f'Welcome to the {HOSPITAL_NAME} Management System',
    'copyright': HOSPITAL_NAME,
    'search_model': ['patients.Patient', 'pharmacy.Medicine', 'billing.Bill'],
    'user_avatar': None,
    'site_logo': 'images/hospital_logo.png',
    'site_logo_classes': 'img-circle',
    'site_icon': 'images/hospital_logo.png',
    'login_logo': 'images/hospital_logo.png',
    'login_logo_dark': 'images/hospital_logo.png',

    'topmenu_links': [
        {'name': 'View Site', 'url': '/', 'new_window': True},
        {'model': 'accounts.User'},
        {'app': 'patients'},
    ],

    'show_sidebar': True,
    'navigation_expanded': False,
    'hide_apps': [],
    'hide_models': [],
    'order_with_respect_to': [
        'accounts', 'patients', 'appointments', 'consultations', 'laboratory',
        'radiology', 'admissions', 'operation_theatre', 'billing', 'insurance',
        'pharmacy', 'blood_bank', 'nursing', 'documents', 'medical_records',
        'departments', 'doctors', 'website', 'reports', 'finance', 'patient_portal',
    'referrals',
    ],

    # Icons: FontAwesome 5 free classes (bundled with Jazzmin), matched to
    # each app/model so the sidebar reads like a hospital directory board.
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.Group': 'fas fa-users',
        'accounts.User': 'fas fa-user-nurse',
        'accounts.AuditLog': 'fas fa-clipboard-list',

        'patients.Patient': 'fas fa-hospital-user',
        'patients.Visit': 'fas fa-notes-medical',
        'patients.District': 'fas fa-map-marker-alt',
        'patients.Province': 'fas fa-map',
        'patients.InsuranceCompany': 'fas fa-shield-alt',
        'patients.InsuranceCategory': 'fas fa-percentage',

        'departments.Department': 'fas fa-building',
        'doctors.Doctor': 'fas fa-user-md',

        'appointments': 'fas fa-calendar-check',
        'consultations': 'fas fa-stethoscope',

        'laboratory.LabTest': 'fas fa-vial',
        'radiology.RadiologyTest': 'fas fa-x-ray',

        'admissions.Ward': 'fas fa-bed',
        'admissions.Bed': 'fas fa-procedures',
        'admissions.Admission': 'fas fa-door-open',

        'operation_theatre.OTRoom': 'fas fa-door-closed',
        'operation_theatre.Surgery': 'fas fa-user-injured',
        'operation_theatre.OperationType': 'fas fa-cut',

        'billing.Bill': 'fas fa-file-invoice-dollar',
        'billing.BillItem': 'fas fa-receipt',
        'billing.RefundRequest': 'fas fa-undo-alt',
        'billing.DiscountRequest': 'fas fa-hand-holding-usd',

        'pharmacy.Medicine': 'fas fa-pills',
        'pharmacy.PharmacySale': 'fas fa-cash-register',

        'insurance': 'fas fa-file-medical',
        'blood_bank': 'fas fa-tint',
        'nursing': 'fas fa-user-nurse',
        'documents': 'fas fa-file-archive',
        'medical_records': 'fas fa-folder-open',

        'website.HospitalService': 'fas fa-list-ul',
        'website.Testimonial': 'fas fa-comment-medical',
        'website.GalleryImage': 'fas fa-images',

        'reports': 'fas fa-chart-line',
        'finance': 'fas fa-coins',
        'patient_portal': 'fas fa-laptop-medical',
    },
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',

    'related_modal_active': True,
    'custom_css': None,
    'custom_js': None,
    'show_ui_builder': False,

    'changeform_format': 'horizontal_tabs',
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-primary',
    'accent': 'accent-primary',
    'navbar': 'navbar-white navbar-light',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'flatly',
    'default_theme_mode': 'auto',
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}
