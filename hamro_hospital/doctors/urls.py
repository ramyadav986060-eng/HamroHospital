from django.urls import path
from doctors import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='doctor_list'),
    path('add/', views.doctor_create, name='doctor_create'),
    path('<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),
    path('<int:pk>/deactivate/', views.doctor_delete, name='doctor_delete'),
    path('dashboard/', views.doctor_dashboard, name='dashboard'),
]
