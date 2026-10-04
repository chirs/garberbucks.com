from collections import defaultdict

from money.coverage import season_ranges
from money.models import Salary


def coverage(request):
    """
    Which seasons have salaries on record, for the footer of every page.
    """
    seasons = defaultdict(list)
    rows = (Salary.objects.filter(period='year')
            .values_list('competition__abbreviation', 'season').distinct())
    for competition, season in rows:
        seasons[competition].append(season)

    return {'coverage': [(c, season_ranges(s)) for c, s in sorted(seasons.items())]}
