from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def dollars(value, currency='USD'):
    """
    Whole dollars with thousands separators: 5500000.08 -> $5,500,000.
    Canadian dollars say so: C$27,000,000.
    """
    return '%s$%s' % ('C' if currency == 'CAD' else '', intcomma(round(value)))
