"""
Age-entry helpers (spec section 12).

Registration Counter can type an age like "24 Years", "11 Years 2 Months",
"1 Month", "15 Days", or "2 Days" instead of hunting for an exact Date of
Birth. We parse that free-text age and calculate an *approximate* Date of
Birth from it. The user can still edit the Date of Birth field manually
afterwards - this just fills in a sensible default.
"""
import datetime
import re

_AGE_PATTERN = re.compile(
    r"""
    (?:(?P<years>\d+)\s*(?:y(?:ea)?rs?)\b)?      # "24 years", "24y", "24yr"
    \s*,?\s*
    (?:(?P<months>\d+)\s*(?:m(?:o(?:nth)?s?)?)\b)?  # "2 months", "2mo", "2m"
    \s*,?\s*
    (?:(?P<days>\d+)\s*(?:d(?:ay)?s?)\b)?         # "15 days", "15d"
    """,
    re.IGNORECASE | re.VERBOSE,
)


def parse_age_to_dob(age_text, today=None):
    """
    Parse strings like '24 Years', '11 Years 2 Months', '1 Month', '15 Days',
    '2 Days' and return an approximate datetime.date of birth.

    Returns None if the string has no recognizable years/months/days.
    """
    if not age_text:
        return None
    today = today or datetime.date.today()
    match = _AGE_PATTERN.search(age_text.strip())
    if not match:
        return None
    years = int(match.group('years') or 0)
    months = int(match.group('months') or 0)
    days = int(match.group('days') or 0)
    if years == 0 and months == 0 and days == 0:
        return None

    total_months = years * 12 + months
    year = today.year
    month = today.month - total_months
    while month <= 0:
        month += 12
        year -= 1
    day = today.day
    # Clamp day to the target month's length (e.g. Feb 30 -> Feb 28/29).
    while True:
        try:
            dob = datetime.date(year, month, day)
            break
        except ValueError:
            day -= 1
    dob = dob - datetime.timedelta(days=days)
    return dob


def format_age_from_dob(dob, today=None):
    """Inverse-ish helper: a human string like '24 Years 2 Months' from a DOB."""
    if not dob:
        return ''
    today = today or datetime.date.today()
    years = today.year - dob.year
    months = today.month - dob.month
    days = today.day - dob.day
    if days < 0:
        months -= 1
        # days in previous month
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month != 1 else today.year - 1
        import calendar
        days += calendar.monthrange(prev_year, prev_month)[1]
    if months < 0:
        months += 12
        years -= 1

    if years >= 1:
        parts = [f"{years} Year{'s' if years != 1 else ''}"]
        if months:
            parts.append(f"{months} Month{'s' if months != 1 else ''}")
        return ' '.join(parts)
    if months >= 1:
        parts = [f"{months} Month{'s' if months != 1 else ''}"]
        if days:
            parts.append(f"{days} Day{'s' if days != 1 else ''}")
        return ' '.join(parts)
    return f"{days} Day{'s' if days != 1 else ''}"
