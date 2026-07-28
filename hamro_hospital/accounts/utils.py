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


def create_notification(title, message, role=None, user=None):
    """
    Create a notification for a specific user, or for all users with a specific role.
    """
    from accounts.models import Notification
    Notification.objects.create(
        user=user,
        role=role,
        title=title,
        message=message,
    )
