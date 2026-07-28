from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    path('create/', views.referral_create, name='referral_create'),
    path('create/<int:patient_id>/', views.referral_create, name='referral_create_for_patient'),
    path('create/<int:patient_id>/<str:referral_type>/', views.referral_create, name='referral_create_for_patient_type'),
    path('queue/', views.department_queue, name='department_queue'),
    path('<int:pk>/', views.referral_detail, name='referral_detail'),
    path('<int:pk>/update/', views.referral_update_status, name='referral_update_status'),
    path('<int:pk>/generate-bill/', views.referral_generate_bill, name='referral_generate_bill'),
]
