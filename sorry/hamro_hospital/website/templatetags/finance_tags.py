from django import template

register = template.Library()

@register.filter
def short_amount(value):
    try:
        v = float(value)
    except (ValueError, TypeError):
        return value

    # For formatting 1000 -> 1K, 100000 -> 1L, 10000000 -> 1Cr
    if v >= 10000000:
        short = v / 10000000.0
        return f"{short:g}CR"
    elif v >= 100000:
        short = v / 100000.0
        return f"{short:g}L"
    elif v >= 1000:
        short = v / 1000.0
        return f"{short:g}K"
    else:
        return f"{v:g}"
