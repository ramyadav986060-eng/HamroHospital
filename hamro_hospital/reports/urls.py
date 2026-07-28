from django.urls import path
from reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.revenue_dashboard, name='revenue_dashboard'),
    path('registrations/', views.registration_report, name='registration_report'),
    path('departments/', views.department_report, name='department_report'),
    path('doctors/', views.doctor_report, name='doctor_report'),
    path('counters/', views.counter_report, name='counter_report'),
    path('pharmacy/', views.pharmacy_report, name='pharmacy_report'),
    path('laboratory/', views.laboratory_report, name='laboratory_report'),
    path('nursing/', views.nursing_report, name='nursing_report'),
    path('operation-theatre/', views.ot_report, name='ot_report'),
    path('blood-bank/', views.blood_bank_report, name='blood_bank_report'),
]
