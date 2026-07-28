from django.urls import path
from radiology import views

app_name = 'radiology'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search_patient, name='search_patient'),
    path('patient/<int:patient_id>/new/', views.manual_create, name='manual_create'),
    path('queue/', views.request_queue, name='queue'),
    path('<int:pk>/accept/', views.accept_request, name='accept_request'),
    path('<int:pk>/update/', views.update_report, name='update_report'),
    path('<int:pk>/print/', views.print_report, name='print_report'),
]
