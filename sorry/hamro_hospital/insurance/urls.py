from django.urls import path
from insurance import views

app_name = 'insurance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.patient_lookup, name='patient_lookup'),
    path('patient/<int:patient_id>/claims/', views.patient_claims, name='patient_claims'),
    path('patient/<int:patient_id>/claims/submit/', views.claim_submit, name='claim_submit'),
    path('claim/<int:pk>/review/', views.claim_review, name='claim_review'),
    path('claim/<int:pk>/slip/', views.claim_slip, name='claim_slip'),
    path('reports/claims/', views.claims_report, name='claims_report'),

    path('companies/', views.company_list, name='company_list'),
    path('companies/add/', views.company_create, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
]
