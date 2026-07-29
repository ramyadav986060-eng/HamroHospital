from django.conf import settings
from django.urls import reverse, NoReverseMatch


def hospital_settings(request):
    """
    Makes hospital-wide settings available in every template without
    each view needing to pass them explicitly.
    """
    from accounts.models import HospitalSetting
    setting = HospitalSetting.get_solo()

    from website.models import Announcement, HomeNotification
    from django.db.models import Q
    from django.utils import timezone
    now = timezone.now()
    public_announcements_qs = Announcement.objects.filter(
        is_active=True, publish_at__lte=now,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gte=now)
    ).order_by('-publish_at')
    public_announcements_count = public_announcements_qs.count()
    public_announcements = public_announcements_qs[:8]


    home_notification = HomeNotification.objects.filter(is_active=True).first()

    user_dashboard_url = ''

    unread_notifications = []
    unread_count = 0
    if getattr(request, 'user', None) and request.user.is_authenticated:
        try:
            user_dashboard_url = reverse(request.user.dashboard_url_name())
        except NoReverseMatch:
            user_dashboard_url = reverse('accounts:post_login_redirect')

        from accounts.models import Notification
        from django.db.models import Q
        unread_qs = Notification.objects.filter(is_read=False).filter(
            Q(user=request.user) | Q(role=request.user.role)
        )
        unread_count = unread_qs.count()
        unread_notifications = unread_qs.order_by('-created_at')[:5]

    return {
        'HOSPITAL_NAME': setting.name,
        'HOSPITAL_CODE': settings.HOSPITAL_CODE,
        'HOSPITAL_EMERGENCY_PHONE': setting.emergency_contact,
        'HOSPITAL_EMAIL': setting.email,
        'HOSPITAL_ADDRESS': setting.address,
        'HOSPITAL_WEBSITE': setting.website,
        'HOSPITAL_PAN': setting.pan_number,
        'HOSPITAL_REGISTRATION_NUMBER': setting.registration_number,
        'HOSPITAL_OPENING_HOURS': setting.opening_hours,
        'HOSPITAL_LOGO_URL': setting.logo.url if setting.logo else '/static/images/hospital_logo.png',
        'user_dashboard_url': user_dashboard_url,
        'unread_notifications': unread_notifications,
        'unread_count': unread_count,

        'public_announcements': public_announcements,
        'public_announcements_count': public_announcements_count,
        'home_notification': home_notification,

        'HOSPITAL_SETTING_OBJ': setting,
    }
