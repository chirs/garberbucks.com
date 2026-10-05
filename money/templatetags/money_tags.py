from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

SYMBOLS = {'USD': '$', 'CAD': 'C$', 'GBP': '£', 'EUR': '€'}


@register.filter
def dollars(value, currency='USD'):
    """
    Whole dollars with thousands separators: 5500000.08 -> $5,500,000.
    Canadian dollars say so: C$27,000,000; pounds and euros take their own
    sign: £5,000,000. A loss puts its sign first: -$2,000,000.
    """
    sign = '-' if value < 0 else ''
    return '%s%s%s' % (sign, SYMBOLS.get(currency, '$'), intcomma(round(abs(value))))


@register.filter
def millions(value):
    """
    Dollars in millions, for tables too wide for whole figures: 330000000 -> $330M,
    1350000000 -> $1,350M, -2000000 -> -$2M.
    """
    sign = '-' if value < 0 else ''
    m = abs(float(value)) / 1e6
    text = intcomma(round(m)) if m >= 10 or m == round(m) else ('%.1f' % m)
    return '%s$%sM' % (sign, text)


@register.filter
def fee(value, currency='USD'):
    """
    A transfer fee, always in millions, to two places at most: 22000000 -> $22M,
    12250000 -> $12.25M, 3960000 -> $3.96M, 7000000 in pounds -> £7M.
    """
    text = ('%.2f' % (value / 1e6)).rstrip('0').rstrip('.')
    return '%s%sM' % (SYMBOLS.get(currency, '$'), text)
