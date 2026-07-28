from django.urls import path
from billing import views

app_name = 'billing'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.patient_lookup, name='patient_lookup'),
    path('bill/new/<int:patient_id>/', views.create_bill, name='create_bill'),
    path('bill/<int:pk>/edit/', views.edit_bill, name='edit_bill'),
    path('visit/<int:visit_id>/confirm-payment/', views.confirm_visit_payment, name='confirm_visit_payment'),
    path('bill/<int:pk>/receipt/', views.receipt, name='receipt'),
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
