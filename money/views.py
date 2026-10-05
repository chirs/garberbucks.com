import re
from collections import defaultdict
from datetime import date
from statistics import median

from django.db.models import Count, F, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from bios.models import Bio
from competitions.models import Competition
from money.models import PAY, ExpansionFee, Job, NetWorth, Operator, Owner, Rule, StadiumCost, StaffPay, Sale, Salary, Sponsorship, Transfer, Valuation
from money.templatetags.money_tags import fee
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
    # A season of reported salaries is a handful of stars, not a record to add up.
    salaries = salaries.filter(coverage='full')

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


PARTIAL_LIST = 18   # players per club below which a season's list is not the whole league


def minimum_rows(seasons):
    """
    MLS's minimum salaries season by season, oldest first, against what players
    were actually paid: the median, and how many were paid the senior minimum
    or less. Every season from the first rule on record to the last, so a
    season without one is a gap rather than skipped.
    """
    rules = {r.season: r for r in Rule.objects.filter(competition__slug=MLS)
             if r.senior_minimum or r.reserve_minimum}
    if not rules:
        return []
    medians = {int(s['season']): s for s in seasons
               if s['competition__slug'] == MLS and s['period'] == 'year' and s['season'].isdigit()}
    league = Salary.objects.filter(competition__slug=MLS, period='year', coverage='full')
    rows = []
    for year in range(min(rules), max(rules) + 1):
        rule = rules.get(year)
        summary = medians.get(year)
        senior = rule.senior_minimum if rule else None
        # A list far shorter than a league's rosters (1996's 46 names) is its best-paid
        # players, so counting who sits at the floor would be meaningless.
        partial = summary and summary['players'] < PARTIAL_LIST * max(summary['teams'], 1)
        # The union's lists carry annualized cents: 2019's minimum is $70,250.04.
        at_minimum = (league.filter(season=str(year), base__lt=senior + 1).count()
                      if senior and summary and not partial else None)
        rows.append({
            'season': str(year),
            'period': 'year',
            'url': reverse('season_detail', args=[MLS, year]) if summary else None,
            'senior': senior,
            'reserve': rule.reserve_minimum if rule else None,
            'median': summary['player_median'] if summary else None,
            'players': summary['players'] if summary else None,
            'at_minimum': at_minimum,
            'share': at_minimum / summary['players'] if at_minimum is not None else None,
        })
    return rows


# The jobs a federation's chart follows, each matched on how the 990 words the role.
KEY_ROLES = (
    ("Men's national team coach", 'average', r'^(?=.*\bmnt\b)(?=.*coach)(?!.*assistant)'),
    ("Women's national team coach", 'median', r'^(?=.*\bwnt\b)(?=.*coach)(?!.*assistant)'),
    ('Chief executive', 'budget', r'^(?!.*(?:former|associate|deputy|assistant)).*(?:\bceo\b|chief execut|secretary gen)'),
)


def key_role_rows(staff):
    """
    Each year's pay for the key jobs, adding up two people where one handed over
    to another during the year, oldest first: rows for the chart's panel.
    """
    years = sorted({s.year for s in staff})
    rows = []
    for year in years:
        row = {'season': str(year), 'period': 'year', 'url': None, 'who': {}}
        for name, _, pattern in KEY_ROLES:
            people = [s for s in staff if s.year == year and s.pay and re.search(pattern, s.role, re.I)]
            row[name] = sum(s.pay for s in people) or None
            row['who'][name] = ', '.join(s.name for s in people)
        rows.append(row)
    return rows


def staff_grid(staff):
    """A row per person, a column per year of their pay, the best paid at their peak first."""
    years = sorted({s.year for s in staff})
    people = {}
    for s in staff:
        row = people.setdefault(s.name, {'name': s.name, 'role': s.role, 'by_year': {}, 'sources': []})
        row['by_year'][s.year] = (row['by_year'].get(s.year) or 0) + (s.pay or 0)
        row['role'] = s.role       # the latest, since staff comes oldest first
        row['sources'] += [u for u in s.source_list() if u not in row['sources']]
    rows = sorted(people.values(), key=lambda r: -max(r['by_year'].values()))
    for row in rows:
        row['values'] = [row['by_year'].get(y) for y in years]
    return years, rows


def staff_index(request):
    """
    What the organizations around the league pay the people who run them: the
    federation and the players' union from their public tax filings, the league
    from what the press reported.
    """
    organizations = []
    # Clubs' reported coach pay is on the coaches page.
    for name in (StaffPay.objects.exclude(organization__in=club_names())
                 .values_list('organization', flat=True).distinct().order_by('organization')):
        staff = list(StaffPay.objects.filter(organization=name).order_by('year', '-pay'))
        years, rows = staff_grid(staff)
        organizations.append({'name': name, 'years': years, 'rows': rows,
                              'reported': all(s.coverage == 'reported' for s in staff),
                              'key_roles': key_role_rows(staff) if any(
                                  re.search(KEY_ROLES[0][2], s.role, re.I) for s in staff) else None})
    # The federation first: it has the most, then the union, then the league's reports.
    order = {'United States Soccer Federation': 0, 'MLS Players Association': 1}
    organizations.sort(key=lambda o: order.get(o['name'], 2))
    return render(request, "money/staff.html", {'organizations': organizations, 'key_roles': KEY_ROLES,
                                                'section': 'pay'})


def club_names():
    return set(Team.objects.values_list('name', flat=True))


def coach_rows(jobs):
    """Head-coach stints, interims included, grouped by club in order of the club's first one."""
    by_team = defaultdict(list)
    for job in sorted((j for j in jobs if j.role in Job.COACHES), key=lambda j: j.start):
        by_team[job.team].append(job)
    return sorted(by_team.items(), key=lambda kv: (kv[1][0].start, kv[0].name))


def coach_changes(jobs, today):
    """
    For each year from the first stint on: how many permanent head coaches left
    their job, and the median years they had held it, of those whose dates are
    known closely enough to measure.
    """
    heads = [j for j in jobs if j.role == Job.HEAD]
    if not heads:
        return []
    left = defaultdict(list)
    for j in heads:
        if j.end:
            left[j.end.year].append(j)
    rows = []
    for year in range(today.year, min(j.start.year for j in heads) - 1, -1):
        lengths = [j.length_years() for j in left[year] if j.length_years() is not None]
        rows.append({'year': year, 'left': len(left[year]),
                     'hired': sum(1 for j in heads if j.start.year == year),
                     'median': median(lengths) if lengths else None})
    return rows


def coaches_index(request):
    """
    Every MLS club's head coaches and who ran its soccer side, and what the
    press has reported coaches were paid.
    """
    today = date.today()
    jobs = list(Job.objects.select_related('team'))
    current = sorted((j for j in jobs if j.role == Job.HEAD and j.end is None),
                     key=lambda j: (j.start, j.team.name))
    clubs = club_names()
    teams = {t.name: t for t in Team.objects.filter(name__in=clubs)}
    pay = [{'staff': s, 'team': teams.get(s.organization)}
           for s in StaffPay.objects.filter(organization__in=clubs).order_by('-year', '-pay')]
    coaches = coach_rows(jobs)
    context = {
        'current': current,
        'coaches': coaches,
        'stints': [j for _, stints in coaches for j in stints],
        'changes': coach_changes(jobs, today),
        'gms': sorted((j for j in jobs if j.role == Job.GM and j.end is None),
                      key=lambda j: (j.team.name, j.start)),
        'pay': pay,
        'today': today,
        'section': 'pay',
        }
    return render(request, "money/coaches.html", context)


def pay_index(request):
    """
    Every season with salaries on record, and the minimum salary through them.
    """
    seasons = season_summaries(Salary.objects.all())
    context = {
        'seasons': seasons,
        'minimums': minimum_rows(seasons),
        'section': 'pay',
        }
    return render(request, "money/pay.html", context)


def index(request):
    """The home page, for now MLS's hub."""
    return league_hub(request, Competition.objects.filter(slug=MLS).first())


def competition_detail(request, competition_slug):
    return league_hub(request, get_object_or_404(Competition, slug=competition_slug))


def league_hub(request, competition):
    """
    Everything on record at a league's level, a section per part of the site:
    payroll, transfers, what its clubs are worth, and what it is paid. Each
    section is the headline and leads to the full page.
    """
    context = {'competition': competition, 'section': 'mls' if competition and competition.slug == MLS else None}
    if competition is None:
        return render(request, "money/hub.html", context)

    seasons = season_summaries(Salary.objects.filter(competition=competition))
    budgets, minimums = {}, {}
    for season, budget, minimum in Rule.objects.filter(competition=competition).values_list(
            'season', 'salary_budget', 'senior_minimum'):
        budgets[season], minimums[season] = budget, minimum
    for s in seasons:
        year = int(s['season']) if s['season'].isdigit() else None
        s['salary_budget'] = budgets.get(year)
        s['senior_minimum'] = minimums.get(year)

    transfers = TRANSFERS.filter(competition=competition)
    cash = [t for t in transfers if t.kind == Transfer.TRANSFER and t.currency == 'USD' and t.fee]
    latest = max((t.season for t in transfers), default=None)
    recent = sorted((t for t in transfers if t.season == latest and t.fee), key=lambda t: -t.fee)[:8]

    valuations = list(Valuation.objects.filter(competition=competition))
    lines = average_lines(valuations)
    years = sorted({y for _, _, pts in lines for y in pts}, reverse=True)
    deals = deal_values(ExpansionFee.objects.filter(competition=competition).select_related('team'),
                        Sale.objects.filter(competition=competition).select_related('team'))

    national = list(Sponsorship.objects.filter(competition=competition, kind=Sponsorship.NATIONAL_TV)
                    .order_by('start', 'sponsor'))
    rights = rights_by_year(national, date.today().year)

    heads = list(Job.objects.filter(competition=competition, role=Job.HEAD).select_related('team'))
    last_year = date.today().year - 1

    context.update({
        'seasons': seasons,
        'latest_pay': next((s for s in seasons if s['period'] == 'year'), None),
        'record_in': max((t for t in cash if t.direction == 'in'), key=lambda t: t.fee, default=None),
        'record_out': max((t for t in cash if t.direction == 'out'), key=lambda t: t.fee, default=None),
        'transfer_season': latest,
        'recent_transfers': recent,
        'recent_cols': transfer_columns(recent),
        'value_lines': lines,
        'value_marks': [d for d in deals if d['kind'] != 'club'],
        'value_rows': [{'year': y, 'values': [pts.get(y) for _, _, pts in lines]} for y in years],
        'value_names': [name for name, _, _ in lines],
        'latest_value': next(((y, name, pts[y]) for y in years for name, _, pts in lines if y in pts), None),
        'rights': rights,
        'national': national,
        'latest_rights': next((r for r in reversed(rights) if r['value']), None),
        'league_sponsors': list(Sponsorship.objects.filter(competition=competition, kind=Sponsorship.LEAGUE)
                                .order_by('start')),
        'has_rules': any(budgets.values()) or any(minimums.values()),
        'longest_coach': min((j for j in heads if j.end is None), key=lambda j: j.start, default=None),
        'coach_changes': {'year': last_year,
                          'left': sum(1 for j in heads if j.end and j.end.year == last_year)},
        'reported': list(Salary.objects.filter(competition=competition, coverage='reported')
                         .annotate(pay=PAY).select_related('person', 'team', 'competition').order_by('season', '-pay')),
        })
    return render(request, "money/hub.html", context)


def average_lines(valuations):
    """A line per publisher of its average club value by season: [(name, css, {season: dollars})]."""
    lines = []
    for publisher, css in PUBLISHERS:
        by_season = defaultdict(list)
        for v in valuations:
            if v.publisher == publisher:
                by_season[v.season].append(v.value)
        if by_season:
            lines.append(('%s, average club' % publisher, css,
                          {s: sum(vs) / len(vs) for s, vs in by_season.items()}))
    return lines


# The money grid's columns: (key, heading, title). Each is a dollar figure for
# the season; a missing one is a gap, and the totals add up only what is known.
GRID = (
    ('payroll', 'payroll', 'guaranteed pay of every player on the club\'s list'),
    ('value', 'value', 'that season\'s published valuation, Forbes where both published'),
    ('fees_in', 'transfers in', 'cash fees paid for players that season'),
    ('fees_out', 'transfers out', 'cash fees received for players that season'),
    ('net', 'net transfers', 'fees received less fees paid'),
    ('shirt', 'shirt deal', 'the front-of-shirt sponsor\'s yearly figure'),
    ('stadium', 'stadium deal', 'the naming-rights sponsor\'s yearly figure'),
)


def money_grid(season, sort='payroll'):
    """
    Every MLS club in a season, a row each: payroll, valuation, transfer fees
    in and out, and the yearly shirt and stadium deals. Rows sort by any column,
    biggest first, missing figures last; the totals add what is on record.
    """
    year = int(season)
    league = Salary.objects.filter(competition__slug=MLS, period='year', season=season).exclude(team=None)
    squads = dict(league.values_list('team').annotate(n=Count('id')).values_list('team', 'n'))
    payrolls = dict(league.values_list('team').annotate(total=Sum(PAY)).values_list('team', 'total'))
    teams = Team.objects.filter(id__in=[t for t, n in squads.items() if n >= SQUAD])

    rows = {t.id: dict({k: None for k, _, _ in GRID}, team=t, payroll=payrolls[t.id], titles={}) for t in teams}
    for v in Valuation.objects.filter(team__in=teams, season=year).order_by('-publisher'):
        rows[v.team_id]['value'] = v.value      # Sportico first, so Forbes wins where both published
        rows[v.team_id]['titles']['value'] = '%s %s' % (v.publisher, year)
    for t in Transfer.objects.filter(season=year, kind=Transfer.TRANSFER, currency='USD').exclude(fee=None):
        for team_id, key in ((t.to_team_id, 'fees_in'), (t.from_team_id, 'fees_out')):
            if team_id in rows:
                rows[team_id][key] = (rows[team_id][key] or 0) + t.fee
    for row in rows.values():
        if row['fees_in'] is not None or row['fees_out'] is not None:
            row['net'] = (row['fees_out'] or 0) - (row['fees_in'] or 0)
    for s in Sponsorship.objects.filter(team__in=teams, kind__in=(Sponsorship.SHIRT, Sponsorship.NAMING_RIGHTS),
                                        start__lte=year).exclude(end__lt=year):
        figure = s.figure_for(year)
        key = 'shirt' if s.kind == Sponsorship.SHIRT else 'stadium'
        if figure:
            rows[s.team_id][key] = figure
            rows[s.team_id]['titles'][key] = s.sponsor

    sort = sort if sort in dict((k, h) for k, h, _ in GRID) else 'payroll'
    ordered = sorted(rows.values(), key=lambda r: (r[sort] is None, -(r[sort] or 0), r['team'].name))
    totals = {k: sum(r[k] for r in ordered if r[k] is not None) if any(r[k] is not None for r in ordered) else None
              for k, _, _ in GRID}
    return {
        'rows': [dict(r, cells=[(r[k], r['titles'].get(k)) for k, _, _ in GRID]) for r in ordered],
        'columns': [{'key': k, 'heading': h, 'title': t, 'current': k == sort} for k, h, t in GRID],
        'totals': [totals[k] for k, _, _ in GRID],
        'sort': sort,
    }


def clubs_index(request):
    """
    Every club in the league's latest season, one row each: what it pays, what
    it is worth, who owns it, where it plays and its biggest transfer. Clubs
    from other seasons and leagues follow as a list.
    """
    league = Salary.objects.filter(competition__slug=MLS, period='year')
    season = max((s for s in league.values_list('season', flat=True).distinct() if s.isdigit()),
                 key=int, default=None)
    payrolls = dict(league.filter(season=season).exclude(team=None).values_list('team')
                    .annotate(total=Sum(PAY)).values_list('team', 'total'))
    teams = Team.objects.filter(id__in=payrolls).order_by('name')

    def latest(rows):
        return max(rows, key=lambda r: r[0], default=None)

    values, owners, stadiums, biggest = {}, {}, {}, {}
    for v in Valuation.objects.filter(team__in=teams):
        values[v.team_id] = latest([values.get(v.team_id) or (0, None), (v.season, v)])
    for o in Operator.objects.filter(team__in=teams, end=None).select_related('owner'):
        owners[o.team_id] = latest([owners.get(o.team_id) or (0, None), (o.start or 0, o)])
    this_year = date.today().year
    for s in Sponsorship.objects.filter(team__in=teams, kind=Sponsorship.NAMING_RIGHTS, start__lte=this_year):
        if s.end is None or s.end >= this_year:
            stadiums[s.team_id] = latest([stadiums.get(s.team_id) or (0, None), (s.start, s)])
    for t in TRANSFERS.filter(kind=Transfer.TRANSFER, currency='USD').exclude(fee=None):
        for team_id in {t.from_team_id, t.to_team_id} - {None}:
            if team_id in payrolls and (team_id not in biggest or t.fee > biggest[team_id].fee):
                biggest[team_id] = t

    positions = budget_positions(teams)
    worths = {}
    for w in NetWorth.objects.filter(team__in=teams).order_by('year', 'net_worth'):
        worths[w.team_id] = w    # the latest year, and within it the richest owner
    rows = [{'team': team, 'payroll': payrolls[team.id],
             'position': next((p for p in positions.get(team.id, []) if p['season'] == season), None),
             'value': values.get(team.id, (0, None))[1],
             'owner': owners.get(team.id, (0, None))[1],
             'worth': worths.get(team.id),
             'stadium': stadiums.get(team.id, (0, None))[1],
             'transfer': biggest.get(team.id)} for team in teams]

    seasons = sorted({int(s) for s in league.values_list('season', flat=True).distinct() if s.isdigit()},
                     reverse=True)
    grid_season = request.GET.get('season', season)
    if not (grid_season and grid_season.isdigit() and int(grid_season) in seasons):
        grid_season = season

    context = {
        'season': season,
        'rows': rows,
        'grid_season': grid_season,
        'grid_seasons': seasons,
        'grid': money_grid(grid_season, request.GET.get('sort', 'payroll')) if grid_season else None,
        'others': Team.objects.exclude(id__in=payrolls).order_by('name'),
        'section': 'clubs',
        }
    return render(request, "money/clubs.html", context)


def season_detail(request, competition_slug, season):
    """
    Everyone paid in a season, highest first, and the payroll of each team.
    """
    competition = get_object_or_404(Competition, slug=competition_slug)

    in_season = Salary.objects.filter(competition=competition, season=season, coverage='full')
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
    maximum = mark_over_maximum(salaries, competition, season)

    context = {
        'maximum': maximum,
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
    context['section'] = 'pay'
    context['crumbs'] = [(competition.get_absolute_url(), competition.name)]
    return render(request, "money/season.html", context)


def team_detail(request, slug):
    """
    A team's payroll, season by season.
    """
    team = get_object_or_404(Team, slug=slug)

    context = {
        'team': team,
        'seasons': season_summaries(Salary.objects.filter(team=team)),
        'budget': budget_positions([team]).get(team.id, []),
        'worths': net_worth_grid(list(NetWorth.objects.filter(team=team).select_related('team', 'club_owner'))),
        'stadiums': list(StadiumCost.objects.filter(team=team)),
        'coaches': coach_rows(jobs := list(Job.objects.filter(team=team).select_related('team'))),
        'gms': [j for j in jobs if j.role == Job.GM],
        'assistants': [j for j in jobs if j.role == Job.ASSISTANT],
        'sponsorships': list(Sponsorship.objects.filter(team=team).exclude(kind__in=Sponsorship.TV)
                             .order_by('kind', 'start')),
        'tv_deals': list(Sponsorship.objects.filter(team=team, kind__in=Sponsorship.TV).order_by('start')),
        'transfers': (transfers := list(TRANSFERS.filter(Q(from_team=team) | Q(to_team=team))
                                        .order_by('-season', F('fee').desc(nulls_last=True)))),
        'transfer_cols': transfer_columns(transfers),
        'valuations': list(Valuation.objects.filter(team=team).order_by('-season', 'publisher')),
        'ownership': ownership_by_competition(
            ExpansionFee.objects.filter(team=team).select_related('competition'),
            Sale.objects.filter(team=team).select_related('competition').order_by('year'),
            Operator.objects.filter(team=team).select_related('competition', 'owner').order_by('start')),
        'value_series': [(p, css, {v.season: v.value for v in Valuation.objects.filter(team=team, publisher=p)})
                         for p, css in PUBLISHERS],
        'deal_marks': deal_values(
            ExpansionFee.objects.filter(team=team, competition__slug=MLS).select_related('team'),
            Sale.objects.filter(team=team, competition__slug=MLS).select_related('team')),
        }
    context['section'] = 'clubs'
    context['crumbs'] = [('/clubs/', 'Clubs')]
    return render(request, "money/team.html", context)


def mark_over_maximum(salaries, competition, season):
    """
    Flag each salary paid above the season's maximum budget charge: a player the
    rules let count only that much, so a Designated Player or one bought down
    with allocation money. Returns the maximum, or None where none is on record.
    """
    rule = Rule.objects.filter(competition=competition, season=int(season)).first() if season.isdigit() else None
    maximum = rule.maximum_charge if rule else None
    for s in salaries:
        s.over_maximum = maximum is not None and s.period == 'year' and (s.guaranteed or s.base) > maximum
    return maximum


def budget_positions(teams):
    """
    Each club's MLS payroll against the salary budget, for every season with
    rules on record: {team_id: [row, newest first]}. A row has the payroll,
    the budget, how far over it the club spent, that as a multiple, and how
    many players it paid above the maximum budget charge.
    """
    rules = {r.season: r for r in Rule.objects.filter(competition__slug=MLS)}
    salaries = (Salary.objects.filter(team__in=teams, competition__slug=MLS, period='year',
                                      season__in=[str(s) for s in rules])
                .annotate(pay=PAY).values_list('team_id', 'team__slug', 'season', 'pay'))
    clubs = defaultdict(lambda: {'payroll': 0, 'players': 0, 'above_max': 0})
    for team_id, slug, season, pay in salaries:
        rule = rules[int(season)]
        row = clubs[(team_id, slug, int(season))]
        row['payroll'] += pay
        row['players'] += 1
        if rule.maximum_charge is not None and pay > rule.maximum_charge:
            row['above_max'] += 1

    positions = defaultdict(list)
    for (team_id, slug, season), row in sorted(clubs.items(), key=lambda kv: -kv[0][2]):
        rule = rules[season]
        if row['players'] < SQUAD or not rule.salary_budget:
            continue
        positions[team_id].append({
            'season': str(season),
            'period': 'year',
            'url': reverse('team_season_detail', args=[slug, season]),
            'payroll': row['payroll'],
            'budget': rule.salary_budget,
            'over': row['payroll'] - rule.salary_budget,
            'times': row['payroll'] / rule.salary_budget,
            'above_max': row['above_max'] if rule.maximum_charge is not None else None,
        })
    return positions


def rules_index(request):
    """
    MLS's roster rules season by season: the salary budget, the most one player
    counts against it, the minimum salaries, and the room beyond it.
    """
    competition = get_object_or_404(Competition, slug=MLS)
    rules = list(Rule.objects.filter(competition=competition).order_by('-season'))
    fields = ('maximum_charge', 'senior_minimum', 'reserve_minimum', 'designated_players',
              'general_allocation', 'targeted_allocation', 'roster')
    context = {
        'competition': competition,
        'rules': rules,
        'cols': {f: any(getattr(r, f) is not None for r in rules) for f in fields},
        'section': 'mls',
        'crumbs': [(reverse('index'), competition.name)],
        }
    return render(request, "money/rules.html", context)


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
    maximum = mark_over_maximum(salaries, salaries[0].competition, season)

    context = {
        'maximum': maximum,
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
    context['section'] = 'pay'
    context['crumbs'] = [('/clubs/', 'Clubs'), (team.get_absolute_url(), team.name)]
    return render(request, "money/team_season.html", context)


def person_detail(request, slug):
    """
    What one person was paid, season by season.
    """
    bio = get_object_or_404(Bio, slug=slug)

    salaries = list(Salary.objects.filter(person=bio)
                    .select_related('team', 'competition').order_by('season'))

    transfers = list(TRANSFERS.filter(person=bio).order_by('season', 'reported'))
    if not salaries and not transfers:
        raise Http404("Nothing on record for %s" % bio)

    context = {
        'bio': bio,
        'salaries': salaries,
        'cols': columns(salaries),
        'transfers': transfers,
        'transfer_cols': transfer_columns(transfers),
        }
    context['section'] = 'pay'
    # The player's latest club, from their pay or, failing that, their last move.
    club = next((s.team for s in reversed(salaries) if s.team), None)
    if club is None and transfers:
        club = transfers[-1].to_team or transfers[-1].from_team
    context['crumbs'] = [('/clubs/', 'Clubs')] + ([(club.get_absolute_url(), club.name)] if club else [])
    return render(request, "money/person.html", context)


# Mark styles for the sponsorship chart, by kind of deal.
SPONSOR_MARKS = {Sponsorship.NAMING_RIGHTS: 'fee', Sponsorship.SHIRT: 'sale', Sponsorship.LEAGUE: 'league'}


def sponsorships_index(request):
    """
    Every sponsorship on record: stadiums, shirts, the league.
    """
    deals = Sponsorship.objects.exclude(kind__in=Sponsorship.TV).select_related('team', 'competition')
    kinds = [
        ('Stadium naming rights', deals.filter(kind=Sponsorship.NAMING_RIGHTS)),
        ('Shirt sponsors', deals.filter(kind=Sponsorship.SHIRT)),
        ('League sponsors', deals.filter(kind=Sponsorship.LEAGUE)),
    ]
    marks = []
    for d in deals:
        figure = d.figure_for(d.start)
        if d.start and figure and d.kind in SPONSOR_MARKS:
            marks.append({'year': d.start, 'value': figure, 'kind': SPONSOR_MARKS[d.kind],
                          'href': d.team.get_absolute_url() if d.team else None,
                          'title': '%s: %s, %s%s, %s a year' % (
                              d.start, d.sponsor, d.property,
                              ' (%s)' % d.team.name if d.team else '', fee(figure, d.currency))})

    context = {
        'marks': marks,
        'mark_names': {'fee': 'Stadium naming rights', 'sale': 'Shirt sponsor', 'league': 'League sponsor'},
        'kinds': [(name, list(qs.order_by('team__name', 'start'))) for name, qs in kinds],
        'count': deals.count(),
        'with_figure': deals.exclude(annual=None, total=None).count(),
        }
    context['section'] = 'revenue'
    return render(request, "money/sponsorships.html", context)


def rights_by_year(deals, last):
    """
    A league's national TV money season by season, from its first deal to the
    last season that has begun: the reported or worked-out yearly figures of
    every deal covering it. A season with no figure has value None, whether its
    deals went unreported or it had none on record; a season with some figures
    counts the rest as unreported, not zero.
    """
    deals = [d for d in deals if d.start]
    if not deals:
        return []
    rows = []
    last = min(last, max(d.end or d.start for d in deals))
    for year in range(min(d.start for d in deals), last + 1):
        covering = [d for d in deals if d.start <= year <= (d.end or d.start)]
        figures = [(d, d.figure_for(year)) for d in covering]
        known = [f for _, f in figures if f is not None]
        rows.append({
            'year': year,
            'value': sum(known) if known else None,
            'paid': [(d, f) for d, f in figures if f is not None],
            'unreported': [d for d, f in figures if f is None],
        })
    return rows


def tv_index(request):
    """
    TV and streaming rights: each league's national deals, with a chart of what
    they paid by season, and clubs' local deals.
    """
    tv = Sponsorship.objects.filter(kind__in=Sponsorship.TV).select_related('team', 'competition')
    leagues = []
    for competition in Competition.objects.filter(sponsorship__kind__in=Sponsorship.TV).distinct().order_by('name'):
        national = list(tv.filter(competition=competition, kind=Sponsorship.NATIONAL_TV).order_by('start', 'sponsor'))
        local = list(tv.filter(competition=competition, kind=Sponsorship.LOCAL_TV).order_by('team__name', 'start'))
        years = rights_by_year(national, date.today().year)
        leagues.append({'competition': competition, 'national': national, 'local': local, 'years': years})
    # MLS first: it is the league with the money and the record.
    leagues.sort(key=lambda l: l['competition'].slug != MLS)
    return render(request, "money/tv.html", {'leagues': leagues, 'count': tv.count(), 'section': 'revenue'})


TRANSFERS = Transfer.objects.select_related('person', 'competition', 'from_team', 'to_team')


def transfer_columns(transfers):
    """Columns worth showing: a ceiling or a kind other than a cash fee only where one is on record."""
    return {
        'ceiling': any(t.ceiling for t in transfers),
        'kind': any(t.kind != Transfer.TRANSFER for t in transfers),
    }


# Mark styles for the transfer chart, by direction, reusing the valuation chart's
# colours: blue in, orange out, faint grey between the league's own clubs.
MOVES = {'in': 'fee', 'out': 'sale', 'within': 'club'}
MOVE_NAMES = {'fee': 'Signed from abroad', 'sale': 'Sold abroad', 'club': 'Between MLS clubs'}


def transfers_index(request):
    """
    Every transfer fee on record, season by season, biggest first, with a
    chart of each cash fee in dollars.
    """
    everything = TRANSFERS.order_by('-season', F('fee').desc(nulls_last=True), 'person__name')
    move = request.GET.get('move')
    if move not in MOVES:
        move = None
    american = request.GET.get('nationality') == 'usa'
    transfers = everything.filter(direction=move) if move else everything
    if american:
        # Only what the player's bio records: a player whose nationality is not
        # on record yet is left out, not guessed at.
        transfers = transfers.filter(person__nationality__iexact='USA', kind=Transfer.TRANSFER).exclude(fee=None)
    transfers = list(transfers)

    marks = [{'year': t.season, 'value': t.fee, 'kind': MOVES[t.direction],
              'href': t.person.get_absolute_url(),
              'title': '%s: %s, %s to %s, %s' % (t.season, t.person.name, t.from_name,
                                                t.to_name or 'an unnamed club', fee(t.fee))}
             for t in transfers
             if t.kind == Transfer.TRANSFER and t.fee and t.currency == 'USD']

    seasons = defaultdict(list)
    for t in transfers:
        seasons[t.season].append(t)
    cash = [t for t in everything if t.kind == Transfer.TRANSFER and t.currency == 'USD' and t.fee]

    context = {
        'seasons': [(season, rows, transfer_columns(rows)) for season, rows in seasons.items()],
        'marks': marks,
        'names': MOVE_NAMES,
        'count': len(transfers),
        'american': american,
        'ranked': sorted(transfers, key=lambda t: -t.fee) if american else None,
        'ranked_cols': transfer_columns(transfers),
        'move': move,
        'moves': [(None, 'All'), ('in', 'Into MLS'), ('out', 'Out of MLS'), ('within', 'Within MLS')],
        'record_in': max((t for t in cash if t.direction == 'in'), key=lambda t: t.fee, default=None),
        'record_out': max((t for t in cash if t.direction == 'out'), key=lambda t: t.fee, default=None),
        }
    context['section'] = 'transfers'
    return render(request, "money/transfers.html", context)


PUBLISHERS = (('Forbes', 'average'), ('Sportico', 'median'))
MLS = 'major-league-soccer'


def money(value):
    return '$' + format(round(value), ',')


TOKEN = 1000   # a sale price below this is nominal


def deal_values(fees, sales):
    """
    The club values that expansion fees and sales put on record, as chart marks
    and table rows. A fee is what a new club cost. A sale counts when it stated
    the value it put on the whole club, or sold the whole club, so its price is
    that value; a partial stake with no stated valuation is left out rather than
    scaled up, and so is a token price (Warner's $1 for the Cosmos in 1971),
    which is a way of taking on a club's debts, not a value.
    """
    rows = []
    for f in fees:
        if f.fee is not None:
            rows.append({'year': f.awarded, 'value': f.fee, 'kind': 'fee', 'team': f.team,
                         'href': f.team.get_absolute_url(),
                         'what': 'expansion fee, first season %s' % f.first_season,
                         'title': '%s %s expansion fee: %s' % (f.awarded, f.team.name, money(f.fee))})
    for s in sales:
        if s.valuation is not None:
            value, what = s.valuation, '%s sold%s' % (s.stake or 'a stake', ' for %s' % money(s.price) if s.price else '')
        elif s.price is not None and s.stake == '100%' and s.price >= TOKEN:
            value, what = s.price, 'the whole club sold'
        else:
            continue
        rows.append({'year': s.year, 'value': value, 'kind': 'sale', 'team': s.team, 'what': what,
                     'href': s.team.get_absolute_url(),
                     'title': '%s %s sale (%s): club valued at %s' % (s.year, s.team.name, what, money(value))})
    return sorted(rows, key=lambda r: (r['year'], r['team'].name))


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
    Every MLS club valuation on record: the published lists, their averages by
    year, and the values that sales and expansion fees put on clubs since 1996.
    """
    valuations = list(Valuation.objects.select_related('team').order_by('season', 'rank'))

    lines, grids = average_lines(valuations), []
    for name, _, averages in lines:
        publisher = name.split(',')[0]
        seasons, rows = valuation_grid([v for v in valuations if v.publisher == publisher])
        grids.append({'publisher': publisher, 'seasons': seasons, 'rows': rows,
                      'averages': [averages[s] for s in seasons]})

    deals = deal_values(
        ExpansionFee.objects.filter(competition__slug=MLS).select_related('team'),
        Sale.objects.filter(competition__slug=MLS).select_related('team'))
    marks = [{'year': v.season, 'value': v.value, 'kind': 'club', 'href': v.team.get_absolute_url(),
              'title': '%s %s value of %s: %s' % (v.season, v.publisher, v.team.name, money(v.value))}
             for v in valuations] + deals

    context = {
        'lines': lines,
        'marks': marks,
        'deals': deals,
        'grids': grids,
        'lists': len({(v.publisher, v.season) for v in valuations}),
        }
    context['section'] = 'value'
    return render(request, "money/valuations.html", context)


def ownership_by_competition(fees, sales, operators):
    """
    [{competition, fees, sales, operators}], one per league with any record,
    the league with the most recent record first.
    """
    leagues = {}
    for kind, rows in (('fees', fees), ('sales', sales), ('operators', operators)):
        for row in rows:
            league = leagues.setdefault(row.competition_id, {
                'competition': row.competition, 'fees': [], 'sales': [], 'operators': []})
            league[kind].append(row)
    latest = lambda l: max([r.start or 0 for r in l['operators']] + [r.year for r in l['sales']] +
                           [r.first_season for r in l['fees']] + [0])
    return sorted(leagues.values(), key=latest, reverse=True)


def net_worth_grid(worths):
    """
    One row per owner and club, a column per year: (years, rows), richest by
    their latest figure first.
    """
    years = sorted({w.year for w in worths})
    owners = {}
    for w in worths:
        row = owners.setdefault((w.owner, w.team_id), {'owner': w.owner, 'team': w.team, 'note': w.note,
                                                      'club_owner': w.club_owner, 'by_year': {}, 'sources': []})
        row['by_year'][w.year] = w.net_worth
        row['sources'] += [s for s in w.source_list() if s not in row['sources']]
    rows = list(owners.values())
    for row in rows:
        row['values'] = [row['by_year'].get(y) for y in years]
        row['latest'] = row['by_year'][max(row['by_year'])]
    rows.sort(key=lambda r: -r['latest'])
    return years, rows


def owner_detail(request, slug):
    """
    One owner: the clubs they ran, the groups they ran clubs as part of, the
    stakes they bought and sold, and what Forbes said they were worth.
    """
    owner = get_object_or_404(Owner, slug=slug)

    operated = list(Operator.objects.filter(owner=owner).select_related('team', 'competition', 'owner')
                    .order_by('start', 'team__name'))
    # A group's record names its members; a member with a page of their own sees it too.
    groups = [o for o in Operator.objects.exclude(owner=owner).select_related('team', 'competition', 'owner')
              .order_by('start') if len(owner.name) > 4 and owner.name in o.operator]
    sales = list(Sale.objects.filter(Q(buyer__contains=owner.name) | Q(seller__contains=owner.name))
                 .select_related('team', 'competition').order_by('year'))
    worths = list(NetWorth.objects.filter(club_owner=owner).select_related('team', 'club_owner'))

    context = {
        'owner': owner,
        'operated': operated,
        'groups': groups,
        'sales': sales,
        'worths': net_worth_grid(worths),
        'worth_list': worths,
        'section': 'value',
        'crumbs': [(reverse('ownership_index'), 'Ownership')],
        }
    return render(request, "money/owner.html", context)


# Mark styles for the stadium chart: built blue, rebuilt orange, the public money grey.
STADIUM_MARKS = {StadiumCost.BUILT: 'fee', StadiumCost.REBUILT: 'sale'}
STADIUM_NAMES = {'fee': 'Built', 'sale': 'Rebuilt', 'club': 'Public money in it'}


def stadiums_index(request):
    """
    What MLS clubs' stadiums cost to build, by the year they opened, and the
    public money reports say went into them.
    """
    stadiums = list(StadiumCost.objects.select_related('team', 'competition'))
    dollars = [s for s in stadiums if s.currency == 'USD' and s.cost]
    marks = []
    for s in dollars:
        marks.append({'year': s.opened, 'value': s.cost, 'kind': STADIUM_MARKS[s.kind],
                      'href': s.team.get_absolute_url(),
                      'title': '%s: %s (%s), %s %s' % (s.opened, s.stadium, s.team.name, s.kind, fee(s.cost))})
        if s.public:
            marks.append({'year': s.opened, 'value': s.public, 'kind': 'club', 'href': s.team.get_absolute_url(),
                          'title': '%s: %s, %s of public money' % (s.opened, s.stadium, fee(s.public))})
    known = [s for s in dollars if s.public is not None]
    context = {
        'stadiums': stadiums,
        'marks': marks,
        'names': STADIUM_NAMES,
        'total': sum(s.cost for s in dollars),
        'with_public': len(known),
        'public_total': sum(s.public for s in known),
        'public_of': sum(s.cost for s in known),
        'section': 'value',
        }
    return render(request, "money/stadiums.html", context)


def ownership_index(request):
    """
    What clubs have paid to join each league, what they have sold for, and who
    has run each of them.
    """
    years, worths = net_worth_grid(list(NetWorth.objects.select_related('team', 'club_owner')))
    context = {
        'worth_years': years,
        'worths': worths,
        'leagues': ownership_by_competition(
            ExpansionFee.objects.select_related('team', 'competition'),
            Sale.objects.select_related('team', 'competition'),
            Operator.objects.select_related('team', 'competition', 'owner')),
        }
    context['section'] = 'value'
    return render(request, "money/ownership.html", context)
