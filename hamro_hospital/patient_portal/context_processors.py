from patient_portal.decorators import get_portal_patient


def portal_patient_context(request):
    """Makes the logged-in Patient Portal account (or None) available in every template."""
    return {'portal_patient': get_portal_patient(request)}
