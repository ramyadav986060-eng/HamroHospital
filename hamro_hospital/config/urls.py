"""
Root URL configuration for the Hamro Hospital Management System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('website.urls')),
    path('accounts/', include('accounts.urls')),
    path('manage/departments/', include('departments.urls')),
    path('manage/doctors/', include('doctors.urls')),
    path('patients/', include('patients.urls')),
    path('appointments/', include('appointments.urls')),
    path('consultations/', include('consultations.urls')),
    path('laboratory/', include('laboratory.urls')),
    path('radiology/', include('radiology.urls')),
    path('admissions/', include('admissions.urls')),
    path('billing/', include('billing.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('insurance/', include('insurance.urls')),
    path('reports/', include('reports.urls')),
    path('portal/', include('patient_portal.urls')),
    path('documents/', include('documents.urls')),
    path('nursing/', include('nursing.urls')),
    path('operation-theatre/', include('operation_theatre.urls')),
    path('blood-bank/', include('blood_bank.urls')),
    path('finance/', include('finance.urls')),
    path('referrals/', include('referrals.urls')),
    path('medical-records/', include('medical_records.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
