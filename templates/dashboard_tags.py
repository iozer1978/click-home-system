from django import template
from django.db.models import Sum
from proposals.models import Quote

register = template.Library()

@register.simple_tag
def get_dashboard_stats():
    total = Quote.objects.count()
    signed = Quote.objects.filter(status='SIGNED').count()
    waiting = Quote.objects.filter(status='DRAFT').count()
    revenue = Quote.objects.filter(status__in=['SIGNED', 'DEPOSIT', 'PRODUCTION', 'COMPLETED']).aggregate(Sum('final_price'))['final_price__sum'] or 0
    return {'total': total, 'signed': signed, 'waiting': waiting, 'revenue': revenue}