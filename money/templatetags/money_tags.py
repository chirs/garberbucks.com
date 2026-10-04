from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def dollars(value):
    """
    Whole dollars with thousands separators: 5500000.08 -> $5,500,000.
    """
    return '$%s' % intcomma(round(value))
