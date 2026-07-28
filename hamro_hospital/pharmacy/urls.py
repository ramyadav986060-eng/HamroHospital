from django.urls import path
from pharmacy import views

app_name = 'pharmacy'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.patient_lookup, name='patient_lookup'),
    path('dispense/<int:patient_id>/', views.dispense, name='dispense'),
    path('sale/<int:pk>/receipt/', views.receipt, name='receipt'),
    path('sale/<int:pk>/reprint/', views.reprint_receipt, name='reprint_receipt'),
    path('sales/today/', views.todays_sales, name='todays_sales'),

    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.medicine_create, name='medicine_create'),
    path('medicines/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('medicines/<int:pk>/adjust-stock/', views.stock_adjust, name='stock_adjust'),
]
