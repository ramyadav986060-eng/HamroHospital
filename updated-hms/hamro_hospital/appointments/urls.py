from django.urls import path
from appointments import views

app_name = 'appointments'

urlpatterns = [
    path('book/', views.book_appointment, name='book_appointment'),
    path('pay/<uuid:transaction_uuid>/', views.pay_appointment, name='pay'),
    path('esewa/success/', views.esewa_success, name='esewa_success'),
    path('esewa/failure/', views.esewa_failure, name='esewa_failure'),
    path('receipt/<uuid:transaction_uuid>/', views.appointment_receipt, name='receipt'),
]
