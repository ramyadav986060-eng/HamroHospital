from django.urls import path
from billing import views

app_name = 'billing'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/details/', views.dashboard_details, name='dashboard_details'),
    path('search/', views.patient_lookup, name='patient_lookup'),
    path('bill/new/<int:patient_id>/', views.create_bill, name='create_bill'),
    path('bill/<int:pk>/edit/', views.edit_bill, name='edit_bill'),
    path('visit/<int:visit_id>/confirm-payment/', views.confirm_visit_payment, name='confirm_visit_payment'),
    path('bill/<int:pk>/receipt/', views.receipt, name='receipt'),
    path('bill/<int:pk>/pay/', views.pay_pending_bill, name='pay_pending_bill'),
    path('bill/<int:pk>/pay/esewa/', views.pay_pending_bill_esewa, name='pay_pending_bill_esewa'),
    path('esewa/success/', views.bill_esewa_success, name='bill_esewa_success'),
    path('esewa/failure/', views.bill_esewa_failure, name='bill_esewa_failure'),
    path('bills/pay-selected/', views.pay_selected_bills, name='pay_selected_bills'),
    path('bill/<int:pk>/reprint/', views.reprint_receipt, name='reprint_receipt'),
    path('collections/today/', views.todays_collections, name='todays_collections'),
    path('bill/<int:pk>/refund/', views.refund_request, name='refund_request'),
    path('bill/<int:pk>/discount/', views.discount_request, name='discount_request'),
    path('bill/<int:pk>/invoice.pdf', views.invoice_pdf, name='invoice_pdf'),
    path('refunds/', views.refund_review_list, name='refund_review_list'),
    path('refunds/<int:pk>/', views.refund_review, name='refund_review'),
    path('discounts/', views.discount_review_list, name='discount_review_list'),
    path('discounts/<int:pk>/', views.discount_review, name='discount_review'),
]
