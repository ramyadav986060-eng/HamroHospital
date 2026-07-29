from django.urls import path
from operation_theatre import views

app_name = 'operation_theatre'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('surgeries/', views.surgery_list, name='surgery_list'),
    path('patient-lookup/', views.patient_lookup, name='patient_lookup'),
    path('schedule/<int:patient_id>/', views.surgery_schedule, name='surgery_schedule'),
    path('<int:pk>/', views.surgery_detail, name='surgery_detail'),
    path('<int:pk>/slip/', views.surgery_slip, name='surgery_slip'),
]
