from django.urls import path
from patient_portal import views

app_name = 'patient_portal'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('register/', views.register_start, name='register_start'),
    path('register/verify/', views.register_verify, name='register_verify'),
    path('register/password/', views.register_password, name='register_password'),
    path('login/', views.login_view, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('book-visit/', views.book_visit, name='book_visit'),
    path('book-visit/<int:visit_id>/pay/', views.pay_visit, name='pay_visit'),
    path('book-visit/esewa/success/', views.visit_esewa_success, name='visit_esewa_success'),
    path('book-visit/esewa/failure/', views.visit_esewa_failure, name='visit_esewa_failure'),

    path('timeline/', views.my_timeline, name='my_timeline'),

    path('visits/', views.my_visits, name='my_visits'),
    path('visits/<int:visit_id>/ticket/', views.my_ticket, name='my_ticket'),
    path('patient-card/', views.my_patient_card, name='my_patient_card'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),

    path('bills/', views.my_bills, name='my_bills'),
    path('bills/<int:pk>/receipt/', views.my_bill_receipt, name='my_bill_receipt'),
    path('bills/<int:pk>/pay/', views.pay_bill, name='pay_bill'),
    path('bills/esewa/success/', views.bill_esewa_success, name='bill_esewa_success'),
    path('bills/esewa/failure/', views.bill_esewa_failure, name='bill_esewa_failure'),

    path('pharmacy-sales/', views.my_pharmacy_sales, name='my_pharmacy_sales'),
    path('pharmacy-sales/<int:pk>/receipt/', views.my_pharmacy_receipt, name='my_pharmacy_receipt'),

    path('prescriptions/', views.my_prescriptions, name='my_prescriptions'),

    path('lab-reports/', views.my_lab_reports, name='my_lab_reports'),
    path('lab-reports/<int:pk>/', views.my_lab_report_detail, name='my_lab_report_detail'),

    path('radiology-reports/', views.my_radiology_reports, name='my_radiology_reports'),
    path('radiology-reports/<int:pk>/', views.my_radiology_report_detail, name='my_radiology_report_detail'),

    path('documents/', views.my_documents, name='my_documents'),
    path('documents/<int:pk>/download/', views.my_document_download, name='my_document_download'),

    path('admissions/', views.my_admissions, name='my_admissions'),
    path('insurance-claims/', views.my_insurance_claims, name='my_insurance_claims'),
]
