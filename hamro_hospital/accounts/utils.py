def get_client_ip(request):
    """Best-effort client IP extraction (handles reverse-proxy X-Forwarded-For)."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def write_audit_log(request, action, description, patient_id_text='', receipt_number='',
                     amount=None, payment_method=''):
    """
    Shared helper used by every app to write one append-only AuditLog row.

    Usage:
        from accounts.utils import write_audit_log
        from accounts.models import AuditLog
        write_audit_log(request, AuditLog.Action.PATIENT_REGISTER,
                         f"Registered patient {patient.patient_code}",
                         patient_id_text=patient.patient_code)
    """
    from accounts.models import AuditLog  # local import avoids circular imports

    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user,
        role_at_time=getattr(user, 'role', ''),
        action=action,
        description=description,
        patient_id_text=patient_id_text,
        receipt_number=receipt_number,
        amount=amount,
        payment_method=payment_method,
        ip_address=get_client_ip(request),
    )


def create_notification(title, message, role=None, user=None, related_url=''):
    """
    Create a notification for a specific user, or for all users with a specific role.
    related_url is optional and lets department staff open the relevant record directly.
    """
    from accounts.models import Notification
    notification = Notification.objects.create(
        user=user,
        role=role,
        title=title,
        message=message,
        related_url=related_url or '',
    )
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        payload = {
            'id': notification.id,
            'title': title,
            'message': message,
            'related_url': related_url or '',
        }
        if user_id := getattr(user, 'id', None):
            async_to_sync(channel_layer.group_send)(f'user_{user_id}', {'type': 'notify', 'payload': payload})
        if role:
            async_to_sync(channel_layer.group_send)(f'role_{role}', {'type': 'notify', 'payload': payload})
    except Exception:
        # WebSocket delivery is best-effort; database notification is authoritative.
        pass
    return notification
