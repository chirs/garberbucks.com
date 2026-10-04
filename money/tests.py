from decimal import Decimal

import pytest

from bios.models import Bio
from competitions.models import Competition
from money.coverage import season_ranges
from money.models import Salary
from money.templatetags.charts import compact, latest_run, payroll_chart
from money.templatetags.money_tags import dollars
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


def summary(season, total, team_average=None, team_median=None, period='year'):
    return {'season': season, 'period': period, 'total': total, 'team_average': team_average,
            'team_median': team_median, 'competition__slug': 'major-league-soccer'}


def test_latest_run_stops_at_a_missing_season():
    seasons = [summary(s, 1) for s in ('2006', '1996', '2004', '2005')]
    assert [s['season'] for s in latest_run(seasons)] == ['2004', '2005', '2006']


def test_latest_run_leaves_out_wages_that_are_not_annual():
    seasons = [summary('1924', 1, period='week'), summary('1925', 1), summary('1926', 1)]
    assert [s['season'] for s in latest_run(seasons)] == ['1925', '1926']


def test_no_chart_for_fewer_than_three_seasons():
    assert payroll_chart([summary('2025', 1), summary('2026', 2)]) == {}


def test_chart_draws_team_payroll_only_where_clubs_are_on_record():
    seasons = [summary('2004', 100), summary('2005', 200), summary('2006', 300, 30, 20),
               summary('2007', 400, 40, 30), summary('2008', 500, 50, 60)]
    chart = payroll_chart(seasons)

    league, average, median = chart['lines']
    assert [line['css'] for line in chart['lines']] == ['league', 'average', 'median']
    assert len(league['points']) == 5
    assert len(average['points']) == len(median['points']) == 3
    assert 'no clubs before 2006' in chart['caption']
    # One unbroken line each: a single move-to.
    assert all(line['path'].count('M') == 1 for line in chart['lines'])


def test_chart_scales_each_side_to_its_own_measure():
    seasons = [summary('2006', 300, 30, 20), summary('2007', 400, 40, 30),
               summary('2008', 630, 50, 60)]
    chart = payroll_chart(seasons)

    top = chart['ticks'][-1]
    assert top['left'] == '$800'      # the league reaches 630
    assert top['right'] == '$60'      # the median reaches 60, past the average
    # Both scales are cut into the same intervals, so one set of gridlines serves both.
    assert len(chart['ticks']) == 5
    # The league and the average both sit on their own scale: 630 of 800, 50 of 60.
    league, average, median = chart['lines']
    assert league['points'][-1]['y'] > median['points'][-1]['y']
    assert 'left scale' in league['legend']['text']
    assert 'right scale' in median['legend']['text']


def test_chart_has_no_right_scale_when_no_clubs_are_on_record():
    chart = payroll_chart([summary(s, 10) for s in ('2004', '2005', '2006')])
    assert [line['name'] for line in chart['lines']] == ['League payroll']
    assert all(t['right'] == '' for t in chart['ticks'])


def squad(competition, team, season, n, each):
    for i in range(n):
        pay('%s %s Player %d' % (team.name, season, i), competition, season, each, each, team)


def test_league_page_charts_payroll_and_averages_it_by_club(client, mls, galaxy):
    fire = Team.objects.create(name='Chicago Fire', slug='chicago-fire')
    for season in '2007', '2008', '2009':
        squad(mls, galaxy, season, 11, 300000)
        squad(mls, fire, season, 11, 100000)

    html = client.get('/c/major-league-soccer/').content.decode()

    assert '<svg' in html
    assert 'League payroll, left scale' in html
    assert 'Average team payroll, right scale' in html
    assert 'Median team payroll, right scale' in html
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
    assert '<svg' not in html        # one season is not a chart


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
