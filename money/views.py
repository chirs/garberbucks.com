from collections import defaultdict
from statistics import median

from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from bios.models import Bio
from competitions.models import Competition
from money.models import PAY, ExpansionFee, Operator, Sale, Salary, Sponsorship, Valuation
from teams.models import Team


# A club listed with fewer players than a team sheet is an expansion side signing
# ahead of its first season (Orlando in 2014, St. Louis in 2022). It has no
# payroll to average yet.
SQUAD = 11


def season_summaries(salaries):
    """
    One row per competition, season and pay period: how many players and
    clubs, what they were paid in all and on average, and who was paid most.
    """
    fields = ('competition_id', 'season', 'period')

    seasons = list(salaries.values(*fields, 'competition__name', 'competition__slug')
                   .annotate(players=Count('id'), total=Sum(PAY))
                   .order_by('-season', 'competition__name'))

    # Players listed without a club count toward the league, not toward any club.
    clubs = defaultdict(list)
    for club in (salaries.exclude(team=None).values(*fields, 'team_id')
                 .annotate(players=Count('id'), total=Sum(PAY))):
        if club['players'] >= SQUAD:
            clubs[tuple(club[f] for f in fields)].append(club['total'])

    pay = defaultdict(list)
    for *key, value in salaries.annotate(pay=PAY).values_list(*fields, 'pay'):
        pay[tuple(key)].append(value)

    top = (salaries.annotate(pay=PAY).select_related('person')
           .order_by(*fields, '-pay').distinct(*fields))
    top = {tuple(getattr(s, f) for f in fields): s for s in top}

    for season in seasons:
        key = tuple(season[f] for f in fields)
        season['top'] = top[key]
        season['teams'] = len(clubs[key])
        season['team_average'] = sum(clubs[key]) / len(clubs[key]) if clubs[key] else None
        season['team_median'] = median(clubs[key]) if clubs[key] else None
        season['player_average'] = season['total'] / season['players']
        season['player_median'] = median(pay[key])

    return seasons


def columns(salaries):
    """
    Which optional columns hold a value in at least one row. A column that is
    empty for every row in the view is left out.
    """
    return {
        'team': any(s.team_id for s in salaries),
        'position': any(s.position for s in salaries),
        'guaranteed': any(s.guaranteed is not None for s in salaries),
    }


def index(request):
    """
    Every season with salaries on record.
    """
    context = {
        'seasons': season_summaries(Salary.objects.all()),
        }
    return render(request, "money/index.html", context)


def competition_detail(request, competition_slug):
    """
    A league's payroll, season by season.
    """
    competition = get_object_or_404(Competition, slug=competition_slug)

    context = {
        'competition': competition,
        'seasons': season_summaries(Salary.objects.filter(competition=competition)),
        }
    return render(request, "money/competition.html", context)


def season_detail(request, competition_slug, season):
    """
    Everyone paid in a season, highest first, and the payroll of each team.
    """
    competition = get_object_or_404(Competition, slug=competition_slug)

    in_season = Salary.objects.filter(competition=competition, season=season)
    salaries = list(in_season.annotate(pay=PAY).select_related('person', 'team')
                    .order_by('-pay', 'person__name'))
    if not salaries:
        raise Http404("No salaries for %s %s" % (competition, season))

    teams = (in_season.exclude(team=None).values('team__name', 'team__slug')
             .annotate(players=Count('id'), total=Sum(PAY))
             .order_by('-total'))

    seasons = sorted(set(Salary.objects.filter(competition=competition)
                         .values_list('season', flat=True)))
    i = seasons.index(season)

    context = {
        'competition': competition,
        'season': season,
        'previous': seasons[i - 1] if i > 0 else None,
        'next': seasons[i + 1] if i + 1 < len(seasons) else None,
        'salaries': salaries,
        'cols': columns(salaries),
        'teams': teams,
        'total': sum(s.pay for s in salaries),
        'average': sum(s.pay for s in salaries) / len(salaries),
        'median': median(s.pay for s in salaries),
        'period': salaries[0].period,
        'sources': sorted(set(s.source for s in salaries if s.source)),
        }
    return render(request, "money/season.html", context)


def team_detail(request, slug):
    """
    A team's payroll, season by season.
    """
    team = get_object_or_404(Team, slug=slug)

    context = {
        'team': team,
        'seasons': season_summaries(Salary.objects.filter(team=team)),
        'sponsorships': list(Sponsorship.objects.filter(team=team).order_by('kind', 'start')),
        'valuations': list(Valuation.objects.filter(team=team).order_by('-season', 'publisher')),
        'operators': list(Operator.objects.filter(team=team).order_by('start')),
        'sales': list(Sale.objects.filter(team=team).order_by('year')),
        'expansion_fee': ExpansionFee.objects.filter(team=team).first(),
        'value_series': [(p, css, {v.season: v.value for v in Valuation.objects.filter(team=team, publisher=p)})
                         for p, css in PUBLISHERS],
        }
    return render(request, "money/team.html", context)


def team_season_detail(request, slug, season):
    """
    Everyone a team paid in a season, highest first.
    """
    team = get_object_or_404(Team, slug=slug)

    salaries = list(Salary.objects.filter(team=team, season=season)
                    .annotate(pay=PAY).select_related('person', 'competition')
                    .order_by('-pay', 'person__name'))
    if not salaries:
        raise Http404("No salaries for %s in %s" % (team, season))

    cols = columns(salaries)
    cols['team'] = False

    context = {
        'team': team,
        'season': season,
        'competition': salaries[0].competition,
        'salaries': salaries,
        'cols': cols,
        'total': sum(s.pay for s in salaries),
        'average': sum(s.pay for s in salaries) / len(salaries),
        'median': median(s.pay for s in salaries),
        'period': salaries[0].period,
        }
    return render(request, "money/team_season.html", context)


def person_detail(request, slug):
    """
    What one person was paid, season by season.
    """
    bio = get_object_or_404(Bio, slug=slug)

    salaries = list(Salary.objects.filter(person=bio)
                    .select_related('team', 'competition').order_by('season'))

    context = {
        'bio': bio,
        'salaries': salaries,
        'cols': columns(salaries),
        }
    return render(request, "money/person.html", context)


def sponsorships_index(request):
    """
    Every sponsorship on record: stadiums, shirts, the league.
    """
    deals = Sponsorship.objects.select_related('team', 'competition')
    kinds = [
        ('Stadium naming rights', deals.filter(kind=Sponsorship.NAMING_RIGHTS)),
        ('Shirt sponsors', deals.filter(kind=Sponsorship.SHIRT)),
        ('League sponsors', deals.filter(kind=Sponsorship.LEAGUE)),
    ]
    context = {
        'kinds': [(name, list(qs.order_by('team__name', 'start'))) for name, qs in kinds],
        'count': deals.count(),
        'with_figure': deals.exclude(annual=None, total=None).count(),
        }
    return render(request, "money/sponsorships.html", context)


PUBLISHERS = (('Forbes', 'average'), ('Sportico', 'median'))


def valuation_grid(valuations):
    """
    For one publisher: the seasons it published, and a row per team holding its
    value in each, None where the team is not on that list.
    """
    seasons = sorted({v.season for v in valuations})
    by_team = defaultdict(dict)
    teams = {}
    for v in valuations:
        by_team[v.team_id][v.season] = v
        teams[v.team_id] = v.team
    latest = seasons[-1] if seasons else None
    rows = sorted(by_team.items(),
                  key=lambda kv: (-(kv[1][latest].value if latest in kv[1] else 0), teams[kv[0]].name))
    return seasons, [(teams[t], [cells.get(s) for s in seasons]) for t, cells in rows]


def valuations_index(request):
    """
    Every published valuation: the league's average by year, and each team's
    value on each list.
    """
    valuations = list(Valuation.objects.select_related('team').order_by('season', 'rank'))

    series = []
    grids = []
    for publisher, css in PUBLISHERS:
        mine = [v for v in valuations if v.publisher == publisher]
        if not mine:
            continue
        by_season = defaultdict(list)
        for v in mine:
            by_season[v.season].append(v.value)
        series.append(('%s, average team' % publisher, css,
                       {s: sum(vs) / len(vs) for s, vs in by_season.items()}))
        seasons, rows = valuation_grid(mine)
        grids.append({'publisher': publisher, 'seasons': seasons, 'rows': rows,
                      'averages': [sum(by_season[s]) / len(by_season[s]) for s in seasons]})

    context = {
        'series': series,
        'grids': grids,
        'lists': len({(v.publisher, v.season) for v in valuations}),
        }
    return render(request, "money/valuations.html", context)


def ownership_index(request):
    """
    What clubs have paid to join the league, what they have sold for, and who
    has run each of them.
    """
    context = {
        'fees': list(ExpansionFee.objects.select_related('team')),
        'sales': list(Sale.objects.select_related('team')),
        'operators': list(Operator.objects.select_related('team')),
        }
    return render(request, "money/ownership.html", context)
