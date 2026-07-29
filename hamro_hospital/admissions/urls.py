from django.urls import path
from admissions import views

app_name = 'admissions'

urlpatterns = [
    path('', views.admission_list, name='admission_list'),
    path('dashboard/details/', views.admission_dashboard_details, name='admission_dashboard_details'),
    path('search/', views.search_patient, name='search_patient'),
    path('admit/<int:patient_id>/', views.admit_patient, name='admit_patient'),
    path('<int:pk>/', views.admission_detail, name='admission_detail'),
    path('<int:pk>/slip/', views.admission_slip, name='admission_slip'),
    path('<int:pk>/deposit/', views.admission_deposit_create, name='admission_deposit_create'),
    path('deposit/<int:pk>/receipt/', views.admission_deposit_receipt, name='admission_deposit_receipt'),
    path('<int:pk>/transfer-bed/', views.admission_transfer_bed, name='admission_transfer_bed'),
    path('<int:pk>/discharge-checklist/', views.update_discharge_checklist, name='update_discharge_checklist'),
    path('<int:pk>/discharge/', views.discharge_patient, name='discharge_patient'),
    path('<int:pk>/discharge-package.pdf', views.discharge_package_pdf, name='discharge_package_pdf'),

    path('wards/', views.ward_list, name='ward_list'),
    path('wards/add/', views.ward_create, name='ward_create'),
    path('beds/add/', views.bed_create, name='bed_create'),
]
