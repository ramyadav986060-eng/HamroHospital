from django.urls import path
from finance import views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('extension-fees/', views.extension_fee_list, name='extension_fee_list'),
    path('extension-fees/<int:pk>/', views.extension_fee_edit, name='extension_fee_edit'),
]
