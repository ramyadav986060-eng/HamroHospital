from django.urls import path
from medical_records import views

app_name = 'medical_records'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.patient_search, name='patient_search'),
    path('patient/<int:patient_id>/', views.patient_full_record, name='patient_full_record'),
]
