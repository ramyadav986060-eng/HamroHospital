from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from patient_portal.models import PatientAccount


def get_portal_patient(request):
    """
    Returns the logged-in PatientAccount for this session, or None.
    Session-based rather than Django's auth backend, since Patient is a
    separate identity space from accounts.User (staff).
    """
    account_id = request.session.get('patient_account_id')
    if not account_id:
        return None
    try:
        return PatientAccount.objects.select_related('patient').get(pk=account_id, is_active=True)
    except PatientAccount.DoesNotExist:
        return None


def patient_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        account = get_portal_patient(request)
        if not account:
            messages.info(request, 'Please log in to your Patient Portal account to continue.')
            return redirect('patient_portal:login')
        request.portal_patient = account
        return view_func(request, *args, **kwargs)
    return _wrapped
