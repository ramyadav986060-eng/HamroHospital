from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.post_login_redirect, name='post_login_redirect'),

    path('dashboard/super-admin/', views.dashboard_super_admin, name='dashboard_super_admin'),

    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/<int:pk>/card/', views.staff_card, name='staff_card'),
    path('staff/attendance/', views.staff_attendance, name='staff_attendance'),
    path('staff/leave/', views.staff_leave_list, name='staff_leave_list'),
    path('staff/leave/request/', views.staff_leave_request, name='staff_leave_request'),
    path('staff/leave/<int:pk>/review/', views.staff_leave_review, name='staff_leave_review'),
    path('staff/api/lookup/', views.staff_lookup_api, name='staff_lookup_api'),
    path('staff/salary/profiles/', views.staff_salary_profiles, name='staff_salary_profiles'),
    path('staff/<int:staff_id>/salary-profile/', views.staff_salary_profile_edit, name='staff_salary_profile_edit'),
    path('staff/salary/generate/', views.staff_salary_generate, name='staff_salary_generate'),
    path('staff/salary/payments/', views.staff_salary_payments, name='staff_salary_payments'),

    path('audit-log/', views.audit_log_list, name='audit_log_list'),
    path('backups/', views.backup_list, name='backup_list'),
    # Backwards-compatible alias for templates/bookmarks that used the old name.
    path('backups/', views.backup_list, name='backups_view'),
    path('backups/create/', views.backup_create, name='backup_create'),
    path('notifications/create/', views.notification_create, name='notification_create'),
    path('notifications/mark-read/', views.mark_all_read, name='mark_all_read'),
    path('settings/', views.hospital_settings_view, name='hospital_settings'),
]
