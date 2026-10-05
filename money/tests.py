from decimal import Decimal

import pytest

from bios.models import Bio
from competitions.models import Competition
from money.coverage import season_ranges
from money.models import ExpansionFee, Operator, Sale, Salary, Sponsorship, Valuation
from money.templatetags.charts import compact, latest_run, log_ticks, payroll_chart, value_chart
from money.templatetags.money_tags import dollars, millions
from teams.models import Team

GAP = '&mdash;'


def test_season_ranges_collapses_runs():
    assert season_ranges(['2005', '1996', '2004', '2006']) == '1996, 2004–2006'


def test_season_ranges_leaves_split_seasons_alone():
    assert season_ranges(['1924-1925', '1925-1926']) == '1924-1925, 1925-1926'


def test_season_ranges_of_nothing():
    assert season_ranges([]) == ''


def test_dollars_rounds_to_whole_dollars():
    assert dollars(Decimal('5500000.08')) == '$5,500,000'
    assert dollars(Decimal('25')) == '$25'


def test_dollars_puts_a_loss_sign_first():
    assert dollars(-16000000) == '-$16,000,000'


def test_dollars_marks_canadian_dollars():
    assert dollars(27000000, 'CAD') == 'C$27,000,000'


@pytest.fixture
def mls(db):
    return Competition.objects.create(name='Major League Soccer', slug='major-league-soccer',
                                      abbreviation='MLS')


@pytest.fixture
def galaxy(db):
    return Team.objects.create(name='LA Galaxy', slug='la-galaxy')


def pay(name, competition, season, base, guaranteed=None, team=None, **kw):
    slug = name.lower().replace(' ', '-')
    person, _ = Bio.objects.get_or_create(slug=slug, defaults={'name': name})
    return Salary.objects.create(person=person, competition=competition, season=season,
                                 base=base, guaranteed=guaranteed, team=team, **kw)


@pytest.fixture
def season_2007(mls, galaxy):
    pay('Landon Donovan', mls, '2007', 900000, 900000, galaxy, position='F')
    pay('David Beckham', mls, '2007', 5500000, 6500000, galaxy, position='M')
    pay('Kenny Schoeni', mls, '2007', 17700, 17700, None, position='GK')


def test_index_lists_each_season_with_its_total_and_top_earner(client, season_2007, mls):
    pay('Marcelo Balboa', mls, '1996', 175000)

    html = client.get('/').content.decode()

    assert html.index('>2007<') < html.index('>1996<')
    assert '$7,417,700' in html
    assert 'David Beckham' in html
    assert 'Marcelo Balboa' in html
    assert 'MLS 1996, 2007' in html


def test_index_renders_with_nothing_on_record(client, db):
    response = client.get('/')
    assert response.status_code == 200
    assert 'none yet' in response.content.decode()


def test_season_page_ranks_players_by_pay(client, season_2007):
    html = client.get('/c/major-league-soccer/2007/').content.decode()

    assert html.index('David Beckham') < html.index('Landon Donovan') < html.index('Kenny Schoeni')
    assert '$6,500,000' in html
    assert 'Payroll by team' in html
    assert '$7,400,000' in html


def test_a_player_listed_without_a_club_is_a_marked_gap(client, season_2007):
    html = client.get('/c/major-league-soccer/2007/').content.decode()

    assert 'title="listed without a club">%s</td>' % GAP in html


def test_columns_empty_for_the_whole_season_are_left_out(client, mls):
    pay('Marcelo Balboa', mls, '1996', 175000)

    html = client.get('/c/major-league-soccer/1996/').content.decode()

    assert '>team<' not in html
    assert '>position<' not in html
    assert '>guaranteed<' not in html
    assert 'Payroll by team' not in html
    assert 'Clubs are not transcribed for this season.' in html
    assert 'The source of these figures was not recorded.' in html
    assert GAP not in html.split('<main')[1].split('</main>')[0]


def test_a_missing_guaranteed_figure_is_a_marked_gap(client, mls):
    pay('Marcelo Balboa', mls, '2004', 175000)
    pay('Freddy Adu', mls, '2004', 300000, 500000)

    html = client.get('/c/major-league-soccer/2004/').content.decode()

    assert 'title="no record found">%s</td>' % GAP in html


def test_season_page_links_the_seasons_either_side(client, mls):
    for season in '2004', '2005', '2006':
        pay('Freddy Adu', mls, season, 300000)

    html = client.get('/c/major-league-soccer/2005/').content.decode()

    assert 'href="/c/major-league-soccer/2004/"' in html
    assert 'href="/c/major-league-soccer/2006/"' in html


def test_season_page_names_its_source(client, mls):
    pay('Freddy Adu', mls, '2006', 300000, source='http://example.com/salaries.html')

    html = client.get('/c/major-league-soccer/2006/').content.decode()

    assert 'href="http://example.com/salaries.html"' in html


def test_a_season_with_no_salaries_is_not_found(client, mls):
    assert client.get('/c/major-league-soccer/1997/').status_code == 404
    assert client.get('/c/no-such-league/2007/').status_code == 404


def test_team_page_lists_its_seasons(client, season_2007, mls, galaxy):
    pay('Landon Donovan', mls, '2008', 900000, 900000, galaxy)

    html = client.get('/teams/la-galaxy/').content.decode()

    assert 'href="/teams/la-galaxy/2007/"' in html
    assert 'href="/teams/la-galaxy/2008/"' in html
    assert '$7,400,000' in html
    assert 'https://soccerstats.us/teams/la-galaxy/' in html


def test_team_season_page_lists_only_that_team(client, season_2007):
    html = client.get('/teams/la-galaxy/2007/').content.decode()

    assert 'David Beckham' in html
    assert 'Kenny Schoeni' not in html
    assert '>team<' not in html


def test_team_pages_that_do_not_exist_are_not_found(client, season_2007):
    assert client.get('/teams/la-galaxy/1999/').status_code == 404
    assert client.get('/teams/no-such-team/').status_code == 404


def test_person_page_lists_salary_by_season(client, mls, galaxy):
    pay('David Beckham', mls, '2008', 5500000, 6500000, galaxy)
    pay('David Beckham', mls, '2007', 5500000, 6500000, galaxy)

    html = client.get('/bios/david-beckham/').content.decode()

    assert html.index('>2007<') < html.index('>2008<')
    assert 'href="/teams/la-galaxy/2007/"' in html
    assert 'https://soccerstats.us/bios/david-beckham/' in html


def test_a_weekly_wage_says_so(client, db):
    asl = Competition.objects.create(name='American Soccer League (1921-1933)',
                                     slug='american-soccer-league-1921-1933', abbreviation='ASL1')
    wonder_workers = Team.objects.create(name='Boston Wonder Workers', slug='boston-wonder-workers')
    pay('Alex McNab', asl, '1925', 25, None, wonder_workers, period='week')

    for url in ('/', '/c/american-soccer-league-1921-1933/1925/', '/teams/boston-wonder-workers/',
                '/teams/boston-wonder-workers/1925/', '/bios/alex-mcnab/'):
        assert '$25 a week' in client.get(url).content.decode(), url

    # A weekly wage is not a season's coverage.
    assert 'ASL1' not in client.get('/').content.decode()


def test_a_person_who_does_not_exist_is_not_found(client, db):
    response = client.get('/bios/no-such-person/')
    assert response.status_code == 404
    assert 'Not found' in response.content.decode()


def test_compact_money():
    assert compact(630955755) == '$631M'
    assert compact(2500000) == '$2.5M'
    assert compact(20000000) == '$20M'
    assert compact(500000) == '$500K'
    assert compact(0) == '$0'
    assert compact(1e9) == '$1B'
    assert compact(1.35e9) == '$1.35B'


def summary(season, total, team_average=None, team_median=None, period='year'):
    return {'season': season, 'period': period, 'total': total, 'team_average': team_average,
            'team_median': team_median, 'player_average': total / 10, 'player_median': total / 20,
            'competition__slug': 'major-league-soccer'}


def test_latest_run_stops_at_a_missing_season():
    seasons = [summary(s, 1) for s in ('2006', '1996', '2004', '2005')]
    assert [s['season'] for s in latest_run(seasons)] == ['2004', '2005', '2006']


def test_latest_run_leaves_out_wages_that_are_not_annual():
    seasons = [summary('1924', 1, period='week'), summary('1925', 1), summary('1926', 1)]
    assert [s['season'] for s in latest_run(seasons)] == ['1925', '1926']


def test_no_chart_for_fewer_than_three_seasons():
    assert payroll_chart([summary('2025', 1), summary('2026', 2)]) == {}


def test_chart_puts_league_and_team_payroll_in_their_own_panels():
    seasons = [summary('2004', 100), summary('2005', 200), summary('2006', 300, 30, 20),
               summary('2007', 400, 40, 30), summary('2008', 630, 50, 60)]
    chart = payroll_chart(seasons)

    league, team, player = chart['panels']
    assert [line['css'] for line in player['lines']] == ['average', 'median']
    assert [line['css'] for line in league['lines']] == ['league']
    assert [line['css'] for line in team['lines']] == ['average', 'median']
    assert len(league['lines'][0]['points']) == 5
    assert all(len(line['points']) == 3 for line in team['lines'])
    assert 'no clubs before 2006' in chart['caption']
    # One unbroken line each: a single move-to.
    assert all(line['path'].count('M') == 1 for p in chart['panels'] for line in p['lines'])
    # Each panel is scaled to its own measures; the team panel holds the median too.
    assert league['ticks'][-1]['text'] == '$800'
    assert team['ticks'][-1]['text'] == '$60'
    # Only the panel with two lines needs a legend.
    assert 'legend' not in league['lines'][0]
    assert all('legend' in line for line in team['lines'])


def test_chart_ends_do_not_overprint():
    seasons = [summary(s, 100, 50, 50) for s in ('2006', '2007', '2008')]
    first, second = payroll_chart(seasons)['panels'][1]['ends']
    assert second['y'] - first['y'] >= 14


def test_chart_has_one_panel_when_no_clubs_are_on_record():
    chart = payroll_chart([summary(s, 10) for s in ('2004', '2005', '2006')])
    assert [p['name'] for p in chart['panels']] == ['League payroll', 'Player pay']


def squad(competition, team, season, n, each):
    for i in range(n):
        pay('%s %s Player %d' % (team.name, season, i), competition, season, each, each, team)


def test_league_page_charts_payroll_and_averages_it_by_club(client, mls, galaxy):
    fire = Team.objects.create(name='Chicago Fire', slug='chicago-fire')
    for season in '2007', '2008', '2009':
        squad(mls, galaxy, season, 11, 300000)
        squad(mls, fire, season, 11, 100000)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert '<figure class="chart"' in html
    assert 'League payroll' in html
    assert 'Average club' in html and 'Median club' in html
    assert '$4,400,000' in html      # the league: 11 x 300k + 11 x 100k
    assert '$2,200,000' in html      # split across two clubs; with two, the median is the same
    assert 'href="/c/major-league-soccer/2008/"' in html


def test_a_club_without_a_squad_is_left_out_of_the_average(client, mls, galaxy):
    orlando = Team.objects.create(name='Orlando City SC', slug='orlando-city-sc')
    squad(mls, galaxy, '2014', 11, 100000)
    pay('Kaka', mls, '2014', 6660000, 7167500, orlando)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert '$8,267,500' in html      # he counts toward the league
    assert '$1,100,000' in html      # the average is the Galaxy alone
    assert '<figure class="chart"' not in html  # one season is not a chart


def test_league_page_marks_a_season_with_no_clubs(client, mls):
    pay('Marcelo Balboa', mls, '1996', 175000)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert 'title="no clubs on record">%s</td>' % GAP in html


def test_a_league_that_does_not_exist_is_not_found(client, db):
    assert client.get('/c/no-such-league/').status_code == 404


def test_home_links_each_season_to_its_league(client, season_2007):
    assert 'href="/c/major-league-soccer/"' in client.get('/').content.decode()


def test_median_team_payroll_is_the_club_in_the_middle(client, mls, galaxy):
    fire = Team.objects.create(name='Chicago Fire', slug='chicago-fire')
    crew = Team.objects.create(name='Columbus Crew', slug='columbus-crew')
    squad(mls, galaxy, '2007', 11, 1000000)
    squad(mls, fire, '2007', 11, 200000)
    squad(mls, crew, '2007', 11, 100000)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert '$4,766,667' in html      # the average, pulled up by the Galaxy
    assert '$2,200,000' in html      # the median: the Fire


def test_a_role_shows_its_group_on_hover(client, mls, galaxy):
    pay('Maya Yoshida', mls, '2024', 500000, 500000, galaxy,
        position='Center-back', position_group='Defender')
    pay('Riqui Puig', mls, '2024', 2000000, 2000000, galaxy,
        position='Midfielder', position_group='Midfielder')

    html = client.get('/c/major-league-soccer/2024/').content.decode()

    assert '<td title="Defender">Center-back</td>' in html
    assert '<td>Midfielder</td>' in html


def test_league_page_gives_average_and_median_salary(client, mls, galaxy):
    pay('David Beckham', mls, '2007', 5500000, 6500000, galaxy)
    pay('Landon Donovan', mls, '2007', 900000, 900000, galaxy)
    pay('Kenny Schoeni', mls, '2007', 17700, 17700, None)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert '>average salary<' in html and '>median salary<' in html
    assert '$2,472,567' in html      # 7,417,700 over three
    assert '$900,000' in html        # the player in the middle


def test_season_page_gives_average_and_median_salary(client, season_2007):
    html = client.get('/c/major-league-soccer/2007/').content.decode()
    assert 'an average of $2,472,567, and a median of $900,000' in html


def deal(competition, team=None, **kw):
    fields = {'kind': Sponsorship.NAMING_RIGHTS, 'sponsor': 'BMO', 'property': 'BMO Stadium',
              'start': 2023, 'end': 2032, 'annual': 10000000, 'total': 100000000,
              'sources': 'https://a.example\nhttps://b.example'}
    fields.update(kw)
    return Sponsorship.objects.create(competition=competition, team=team, **fields)


def test_sponsorships_page_lists_deals_by_kind(client, mls, galaxy):
    deal(mls, galaxy)
    deal(mls, galaxy, kind=Sponsorship.SHIRT, sponsor='Herbalife', property='shirt',
         start=2013, end=2022, annual=4400000, total=44000000)
    deal(mls, None, kind=Sponsorship.LEAGUE, sponsor='Adidas', property='kit supplier',
         start=2005, end=2014, annual=None, total=150000000)

    html = client.get('/sponsorships/').content.decode()

    assert html.index('Stadium naming rights') < html.index('Shirt sponsors') < html.index('League sponsors')
    assert '$10,000,000' in html and '$44,000,000' in html and '$150,000,000' in html
    assert '2023–2032' in html
    assert 'href="https://b.example">2</a>' in html
    assert '3 deals' in html and '3 with a figure' in html
    # Adidas reported a total over ten seasons, so its yearly figure is worked out.
    assert 'class="num inferred" title="worked out: $150,000,000 over 10 seasons">$15,000,000</td>' in html


def test_a_deal_with_no_terms_is_listed_with_marked_gaps(client, mls, galaxy):
    deal(mls, galaxy, sponsor='Q2', property='Q2 Stadium', start=2021, end=None,
         annual=None, total=None, note='terms not disclosed')

    html = client.get('/sponsorships/').content.decode()

    assert 'Q2 Stadium' in html and '2021–' in html
    assert html.count('title="not reported">&mdash;</td>') == 2
    assert '0 with a figure' in html


def test_canadian_dollars_say_so(client, mls):
    toronto = Team.objects.create(name='Toronto FC', slug='toronto-fc')
    deal(mls, toronto, property='BMO Field', annual=None, total=27000000, currency='CAD')

    assert 'C$27,000,000' in client.get('/sponsorships/').content.decode()


def test_team_page_lists_its_sponsorships(client, mls, galaxy):
    pay('Landon Donovan', mls, '2013', 900000, 900000, galaxy)
    deal(mls, galaxy, sponsor='Herbalife', property='shirt', kind=Sponsorship.SHIRT)

    html = client.get('/teams/la-galaxy/').content.decode()

    assert '<h2>Sponsorships</h2>' in html
    assert 'Herbalife' in html
    assert '>club<' not in html


def test_team_page_without_sponsorships_has_no_section(client, season_2007):
    assert 'Sponsorships</h2>' not in client.get('/teams/la-galaxy/').content.decode()


def test_millions():
    assert millions(330000000) == '$330M'
    assert millions(1350000000) == '$1,350M'
    assert millions(-2000000) == '-$2M'
    assert millions(2200000) == '$2.2M'


def test_log_ticks_bracket_the_values():
    assert log_ticks(5e6, 1.45e9) == [5e6, 1e7, 2e7, 5e7, 1e8, 2e8, 5e8, 1e9, 2e9]


def test_value_chart_breaks_the_line_at_a_missing_year():
    chart = value_chart([('Forbes', 'average', {2008: 37e6, 2013: 103e6, 2015: 157e6, 2016: 185e6})], [], 'x')
    (line,) = chart['lines']
    assert len(line['points']) == 4
    assert line['path'].count('M') == 3     # 2008 alone, 2013 alone, 2015-2016 joined


def test_value_chart_starts_where_asked_and_draws_marks():
    marks = [{'year': 1997, 'value': 5e6, 'kind': 'fee', 'title': 'fee'},
             {'year': 2019, 'value': 4e8, 'kind': 'sale', 'title': 'sale'}]
    chart = value_chart([('Forbes', 'average', {2018: 2.4e8, 2019: 3.1e8})], marks, 'x', 1996)
    # The axis starts in 1996, a year before the first mark.
    assert chart['marks'][0]['x'] > chart['left']
    assert [m['kind'] for m in chart['marks']] == ['fee', 'sale']
    assert [i['kind'] for i in chart['legend']] == ['line', 'fee', 'sale']
    fee, sale = chart['marks']
    assert fee['y'] > sale['y']                 # $5M sits below $400M


def test_value_chart_needs_two_years():
    assert value_chart([('Forbes', 'average', {2026: 1e9})], [], 'x') == {}


def valuation(team, competition, publisher, season, value, rank=1, **kw):
    return Valuation.objects.create(team=team, competition=competition, publisher=publisher,
                                    season=season, value=value, rank=rank, **kw)


def test_valuations_page_tables_each_publisher(client, mls, galaxy):
    fire = Team.objects.create(name='Chicago Fire', slug='chicago-fire')
    valuation(galaxy, mls, 'Forbes', 2018, 320000000, 1)
    valuation(fire, mls, 'Forbes', 2018, 245000000, 2)
    valuation(galaxy, mls, 'Forbes', 2019, 480000000, 1)
    valuation(galaxy, mls, 'Sportico', 2026, 1170000000, 1)

    html = client.get('/valuations/').content.decode()

    assert html.index('<h2>Forbes</h2>') < html.index('<h2>Sportico</h2>')
    assert '$320M' in html and '$1,170M' in html
    assert '$282M' in html                       # the 2018 Forbes average, 282.5 rounded to even
    assert 'title="not on this list">&mdash;' in html   # the Fire in 2019
    assert '<figure class="chart"' in html and 'Forbes, average club' in html
    assert '3 published' in html


def test_team_page_lists_its_valuations(client, mls, galaxy):
    valuation(galaxy, mls, 'Forbes', 2018, 320000000, 2, revenue=63000000, operating_income=6000000,
              sources='https://a.example')
    valuation(galaxy, mls, 'Forbes', 2019, 480000000, 2)

    html = client.get('/teams/la-galaxy/').content.decode()

    assert '<h2>Valuations</h2>' in html
    assert '$320,000,000' in html and '$63,000,000' in html
    assert 'title="not given">&mdash;' in html
    assert 'href="https://a.example">1</a>' in html
    assert '<figure class="chart"' in html


@pytest.fixture
def chicago(mls):
    fire = Team.objects.create(name='Chicago Fire', slug='chicago-fire')
    ExpansionFee.objects.create(team=fire, competition=mls, awarded=1997, first_season=1998,
                                fee=5000000, sources='https://a.example')
    Operator.objects.create(team=fire, competition=mls, operator='Anschutz Entertainment Group',
                            start=1997, end=2007)
    Operator.objects.create(team=fire, competition=mls, operator='Joe Mansueto', start=2019, end=None)
    Sale.objects.create(team=fire, competition=mls, year=2019, seller='Andrew Hauptman',
                        buyer='Joe Mansueto', stake='51%', price=204000000, valuation=400000000,
                        sources='https://b.example')
    Sale.objects.create(team=fire, competition=mls, year=2018, seller='Andrew Hauptman',
                        buyer='Joe Mansueto', stake='49%')
    return fire


def test_ownership_page(client, chicago):
    html = client.get('/ownership/').content.decode()

    assert html.index('<h3>Expansion fees</h3>') < html.index('<h3>Sales</h3>') < html.index('<h3>Operators</h3>')
    assert '$5,000,000' in html and '$204,000,000' in html and '$400,000,000' in html
    assert html.index('>2018<') < html.index('>2019<')
    assert 'present' in html
    assert 'title="not reported">&mdash;' in html
    assert 'href="https://b.example">1</a>' in html


def test_team_page_shows_ownership(client, chicago):
    html = client.get('/teams/chicago-fire/').content.decode()

    assert '<h2>Ownership</h2>' in html
    assert 'joined MLS in 1998' in html and 'expansion fee of $5,000,000' in html
    assert 'Joe Mansueto' in html
    assert '>club<' not in html


def test_team_page_for_a_club_with_no_salaries(client, chicago):
    html = client.get('/teams/chicago-fire/').content.decode()
    assert 'No salaries are on record for Chicago Fire' in html


def test_ownership_is_grouped_by_league(client, chicago, db):
    nasl = Competition.objects.create(name='North American Soccer League',
                                      slug='north-american-soccer-league', abbreviation='NASL')
    sounders = Team.objects.create(name='Seattle Sounders', slug='seattle-sounders')
    mls = Competition.objects.get(slug='major-league-soccer')
    ExpansionFee.objects.create(team=sounders, competition=nasl, awarded=1973, first_season=1974, fee=75000)
    ExpansionFee.objects.create(team=sounders, competition=mls, awarded=2007, first_season=2009, fee=30000000)

    html = client.get('/ownership/').content.decode()
    assert html.index('<h2>Major League Soccer</h2>') < html.index('<h2>North American Soccer League</h2>')

    html = client.get('/teams/seattle-sounders/').content.decode()
    assert '<h3>Major League Soccer</h3>' in html and '<h3>North American Soccer League</h3>' in html
    assert 'expansion fee of $75,000' in html and 'expansion fee of $30,000,000' in html


def test_a_club_in_one_league_has_no_league_heading(client, chicago):
    assert '<h3>Major League Soccer</h3>' not in client.get('/teams/chicago-fire/').content.decode()


def test_valuations_page_charts_fees_and_sales(client, mls, galaxy, chicago):
    valuation(galaxy, mls, 'Forbes', 2018, 320000000, 1)

    html = client.get('/valuations/').content.decode()

    assert '<h2>Expansion fees and sales</h2>' in html
    assert 'class="mark-fee"' in html and 'class="mark-sale"' in html
    assert 'class="mark-club"' in html
    assert '<rect' not in html.split('<figure')[1].split('</figure>')[0]   # circles only
    assert 'data-href="/teams/chicago-fire/"' in html
    assert 'class="chart-readout"' in html
    # Mansueto's 51% stated a $400M valuation; the 49% with no figure is left off.
    assert '$400,000,000' in html and '51% sold for $204,000,000' in html
    assert '49% sold' not in html
    assert '1997 Chicago Fire expansion fee: $5,000,000' in html


def test_team_chart_carries_its_own_deals(client, chicago, mls):
    valuation(chicago, mls, 'Forbes', 2018, 245000000, 13)
    valuation(chicago, mls, 'Forbes', 2019, 335000000, 8)

    html = client.get('/teams/chicago-fire/').content.decode()

    assert 'class="mark-fee"' in html and 'class="mark-sale"' in html


def test_a_missing_annual_is_worked_out_from_total_and_length(client, mls, galaxy):
    deal(mls, galaxy, sponsor='Home Depot', property='Home Depot Center', start=2003, end=2012,
         annual=None, total=70000000)

    html = client.get('/sponsorships/').content.decode()

    assert 'class="num inferred" title="worked out: $70,000,000 over 10 seasons">$7,000,000</td>' in html


def test_a_missing_total_is_worked_out_from_annual_and_length(client, mls, galaxy):
    deal(mls, galaxy, sponsor='Dignity Health', property='Dignity Health Sports Park', start=2019,
         end=2028, annual=6000000, total=None)

    html = client.get('/sponsorships/').content.decode()

    assert 'class="num inferred" title="worked out: $6,000,000 a season for 10 seasons">$60,000,000</td>' in html


def test_nothing_is_worked_out_without_a_known_length(client, mls, galaxy):
    deal(mls, galaxy, sponsor='Audi', property='Audi Field', start=2018, end=None,
         annual=4000000, total=None)

    html = client.get('/sponsorships/').content.decode()

    assert 'inferred' not in html.split('<tbody>')[1]
    assert 'title="not reported">&mdash;</td>' in html


def test_a_deal_ended_early_is_worked_out_over_its_contracted_length(client, mls, galaxy):
    deal(mls, galaxy, sponsor='Banc of California', property='Banc of California Stadium',
         start=2018, end=2020, length=15, annual=None, total=100000000)

    html = client.get('/sponsorships/').content.decode()

    assert 'title="worked out: $100,000,000 over 15 seasons">$6,666,667</td>' in html


def tv(competition, team=None, **kw):
    kind = Sponsorship.LOCAL_TV if team else Sponsorship.NATIONAL_TV
    return deal(competition, team, **{'kind': kind, **kw})


def test_tv_deals_get_their_own_page_not_the_sponsorships_page(client, mls, galaxy):
    tv(mls, sponsor='Apple', property='every match, streaming', start=2023, end=2025,
       annual=250000000, total=None)
    tv(mls, galaxy, sponsor='Time Warner Cable SportsNet', property='local TV', start=2012,
       end=2021, annual=None, total=55000000)

    sponsorships = client.get('/sponsorships/').content.decode()
    page = client.get('/tv/').content.decode()

    assert 'Apple' not in sponsorships and 'Time Warner' not in sponsorships
    assert '<th scope="col">broadcaster</th>' in page
    assert 'Apple' in page and "Clubs' local TV" in page
    assert 'title="worked out: $55,000,000 over 10 seasons">$5,500,000</td>' in page


def test_tv_chart_sums_each_season_and_leaves_unreported_seasons_as_gaps(client, mls):
    tv(mls, sponsor='ABC and ESPN', property='TV', start=1996, end=1998, annual=0, total=None)
    tv(mls, sponsor='ABC, ESPN and Univision', property='TV', start=1999, end=2006,
       annual=None, total=None)
    tv(mls, sponsor='ESPN', property='TV', start=2007, end=2014, annual=8000000, total=None)
    tv(mls, sponsor='Univision', property='TV', start=2007, end=2014, annual=None, total=80000000)
    tv(mls, sponsor='Fox', property='TV', start=2011, end=2011, annual=None, total=None)

    html = client.get('/tv/').content.decode()
    chart = html.split('<figure')[1].split('</figure>')[0]

    assert chart.count('class="bar"') == 8              # 2007-2014; 1999-2006 has no figure
    assert chart.count('>$0</text>') == 4               # 1996-1998, no rights fee, and the axis
    assert chart.count('>&ndash;</text>') == 8          # 1999-2006, deals with no figure
    assert 'data-tip="2007: $18M (ESPN $8M; Univision $10M)"' in chart
    assert 'data-tip="2011: $18M (ESPN $8M; Univision $10M; Fox not reported)"' in chart


def test_a_club_page_lists_its_local_tv_deals_apart_from_sponsorships(client, mls, galaxy):
    deal(mls, galaxy)
    tv(mls, galaxy, sponsor='Time Warner Cable SportsNet', property='local TV', start=2012,
       end=2021, annual=None, total=55000000)

    html = client.get('/teams/la-galaxy/').content.decode()

    sponsorships, local = html.split('<h2>Sponsorships</h2>')[1].split('<h2>Local TV</h2>')
    assert 'BMO' in sponsorships and 'Time Warner' not in sponsorships
    assert 'Time Warner' in local


def test_tv_chart_keeps_seasons_with_no_deal_on_the_axis(client, mls):
    tv(mls, sponsor='CBS', property='TV', start=1968, end=1968, annual=500000, total=None)
    tv(mls, sponsor='ABC', property='TV', start=1979, end=1980, annual=None, total=1800000)

    chart = client.get('/tv/').content.decode().split('<figure')[1].split('</figure>')[0]

    assert '>1974</text>' in chart and '&ndash;' not in chart
    assert chart.count('class="bar"') == 3
