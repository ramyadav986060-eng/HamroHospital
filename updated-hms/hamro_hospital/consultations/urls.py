from django.urls import path
from consultations import views

app_name = 'consultations'

urlpatterns = [
    path('queue/', views.consultation_queue, name='queue'),
    path('visit/<int:visit_id>/', views.consultation_detail, name='consultation_detail'),
    path('<int:consultation_id>/lab-request/add/', views.add_lab_request, name='add_lab_request'),
    path('<int:consultation_id>/radiology-request/add/', views.add_radiology_request, name='add_radiology_request'),
    path('patient/<int:patient_id>/history/', views.patient_history, name='patient_history'),
]
