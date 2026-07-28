from django.urls import path
from website import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('departments/', views.department_list, name='department_list'),
    path('departments/<slug:slug>/', views.department_detail, name='department_detail'),
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('medical-services/', views.medical_services, name='medical_services'),
    path('diseases/', views.disease_list, name='disease_list'),
    path('diseases/<slug:slug>/', views.disease_detail, name='disease_detail'),
    path('gallery/', views.gallery, name='gallery'),
    path('contact/', views.contact, name='contact'),
    path('assistant/api/', views.assistant_api, name='assistant_api'),

    path('manage/services/', views.service_list, name='service_list'),
    path('manage/services/add/', views.service_create, name='service_create'),
    path('manage/services/<int:pk>/edit/', views.service_edit, name='service_edit'),
]
