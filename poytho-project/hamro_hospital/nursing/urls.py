from django.urls import path
from nursing import views

app_name = 'nursing'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search_patient, name='search_patient'),
    path('admission/<int:admission_id>/', views.admission_notes, name='admission_notes'),
]
