from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from accounts.models import Role


def role_required(*allowed_roles):
    """
    Restrict a view to one or more staff roles.

    A Django superuser (is_superuser=True) always passes, regardless of
    which roles are listed, matching the "superuser = full Super Admin
    access" rule described in the system documentation.

    Usage:
        @role_required(Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER)
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.effective_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You don't have permission to access that page.")
            return redirect(request.user.dashboard_url_name())
        return _wrapped
    return decorator


def super_admin_required(view_func):
    return role_required(Role.SUPER_ADMIN)(view_func)


def registration_counter_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.REGISTRATION_COUNTER)(view_func)


def doctor_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.DOCTOR)(view_func)


def cash_counter_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.CASH_COUNTER)(view_func)


def billing_counter_required(view_func):
    """Cashier (full access) plus Laboratory/Radiology staff, who may only
    bill their own department's services - see the counter_department
    check inside billing.views.create_bill (spec 5 'Laboratory Counter
    (only for laboratory services)' / spec 6 mirrors it for Radiology)."""
    return role_required(Role.SUPER_ADMIN, Role.CASH_COUNTER, Role.LABORATORY, Role.RADIOLOGY)(view_func)


def pharmacy_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.PHARMACY)(view_func)


def laboratory_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.LABORATORY)(view_func)


def radiology_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.RADIOLOGY)(view_func)


def insurance_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.INSURANCE)(view_func)


def ward_admission_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.WARD_ADMISSION)(view_func)


def nursing_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.NURSING)(view_func)


def operation_theatre_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.OPERATION_THEATRE)(view_func)


def blood_bank_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.BLOOD_BANK)(view_func)


def accounts_dept_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.ACCOUNTS_DEPT)(view_func)


def medical_records_required(view_func):
    return role_required(Role.SUPER_ADMIN, Role.MEDICAL_RECORDS)(view_func)


# Any staff role that legitimately needs to see a patient's full record
# (used by patients.views.patient_detail - editing stays registration-only).
def patient_record_viewer_required(view_func):
    return role_required(*Role.values)(view_func)


# Any staff role at all - used to gate the shared PatientDocument system,
# which every department must be able to use (spec section 3).
def any_staff_required(view_func):
    return role_required(*Role.values)(view_func)
