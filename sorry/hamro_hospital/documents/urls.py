from django.urls import path
from documents import views

app_name = 'documents'

urlpatterns = [
    path('patient/<int:patient_id>/', views.document_list, name='document_list'),
    path('patient/<int:patient_id>/upload/', views.document_upload, name='document_upload'),
    path('<int:pk>/replace/', views.document_replace, name='document_replace'),
    path('<int:pk>/view/', views.document_view, name='document_view'),
    path('<int:pk>/download/', views.document_download, name='document_download'),
    path('<int:pk>/delete/', views.document_delete, name='document_delete'),
]
