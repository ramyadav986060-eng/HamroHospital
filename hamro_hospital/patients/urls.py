from django.urls import path
from patients import views

app_name = 'patients'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.patient_register, name='patient_register'),
    path('search/', views.patient_search, name='patient_search'),
    path('list/', views.patient_list, name='patient_list'),
    path('<int:pk>/', views.patient_detail, name='patient_detail'),
    path('<int:pk>/section/<str:section>/', views.patient_section, name='patient_section'),
    path('<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('<int:pk>/new-visit/', views.patient_new_visit, name='patient_new_visit'),
    path('<int:pk>/card/', views.patient_card, name='patient_card'),
    path('visit/<int:visit_id>/ticket/', views.opd_ticket, name='opd_ticket'),
    path('visit/<int:visit_id>/ticket/reprint/', views.opd_ticket_reprint, name='opd_ticket_reprint'),
    path('ajax/department/<int:department_id>/doctors/', views.get_doctors_for_department, name='ajax_doctors'),
    path('api/lookup/', views.qr_lookup, name='qr_lookup'),
    path('appointment/<int:appointment_id>/confirm/', views.confirm_arrival, name='confirm_arrival'),
    path('appointment/<int:appointment_id>/cancel/', views.cancel_booking, name='cancel_booking'),
]
