from django import template

register = template.Library()


@register.filter
def lines_upto(value, max_count=3):
    """Split text into non-empty lines; return at most max_count strings."""
    try:
        n = int(max_count)
    except (TypeError, ValueError):
        n = 3
    if not value:
        return []
    parts = [p.strip() for p in str(value).replace("\r", "").split("\n") if p.strip()]
    return parts[:n]
