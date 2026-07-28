from django.urls import path
from admissions import views

app_name = 'admissions'

urlpatterns = [
    path('', views.admission_list, name='admission_list'),
    path('search/', views.search_patient, name='search_patient'),
    path('admit/<int:patient_id>/', views.admit_patient, name='admit_patient'),
    path('<int:pk>/', views.admission_detail, name='admission_detail'),
    path('<int:pk>/slip/', views.admission_slip, name='admission_slip'),
    path('<int:pk>/discharge/', views.discharge_patient, name='discharge_patient'),

    path('wards/', views.ward_list, name='ward_list'),
    path('wards/add/', views.ward_create, name='ward_create'),
    path('beds/add/', views.bed_create, name='bed_create'),
]
