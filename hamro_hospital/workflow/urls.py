from django.urls import path
from workflow import views

app_name = 'workflow'

urlpatterns = [
    path('orders/', views.service_order_queue, name='service_order_queue'),
    path('orders/<int:pk>/', views.service_order_detail, name='service_order_detail'),
    path('orders/<int:pk>/update/', views.service_order_update, name='service_order_update'),
    path('payments/', views.payment_events, name='payment_events'),
    path('revenue/', views.department_revenue, name='department_revenue'),
    path('patient/<int:patient_id>/timeline/', views.patient_timeline, name='patient_timeline'),
]
