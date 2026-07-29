from django.urls import path
from blood_bank import views

app_name = 'blood_bank'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('requests/', views.request_queue, name='request_queue'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.unit_add, name='unit_add'),
    path('patient-lookup/', views.patient_lookup, name='patient_lookup'),
    path('issue/<int:patient_id>/', views.issue_blood, name='issue_blood'),

    path('doctor/patient-lookup/', views.doctor_patient_lookup, name='doctor_patient_lookup'),
    path('doctor/request/<int:patient_id>/', views.doctor_request_create, name='doctor_request_create'),
]
