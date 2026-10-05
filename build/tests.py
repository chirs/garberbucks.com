import datetime
from decimal import Decimal

import pytest

from bios.models import Bio
from build import load
from money.models import ExpansionFee, NetWorth, Operator, Owner, Rule, Sale, Salary, Sponsorship, Transfer, Valuation
from teams.models import Team


class FakeCollection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, spec=None):
        names = spec['name']['$in'] if spec else None
        return [dict(r) for r in self.rows if names is None or r['name'] in names]


class FakeDB:
    def __init__(self, **collections):
        for name, rows in collections.items():
            setattr(self, name, FakeCollection(rows))


def salary(**kw):
    e = {'name': 'David Beckham', 'team': 'LA Galaxy', 'position': 'Midfielder',
         'position_group': 'Midfielder',
         'base': '5500000.08', 'guaranteed': '6500000.04',
         'competition': 'Major League Soccer', 'season': '2007',
         'source': 'MLS Players Union', 'period': 'year'}
    e.update(kw)
    return e


@pytest.fixture
def mongo(monkeypatch):
    def use(salaries, bios=(), sponsorships=(), valuations=(), operators=(), sales=(), fees=(), transfers=(), rules=(), worths=(), stadiums=(), staff=()):
        db = FakeDB(
            salaries=salaries,
            sponsorships=list(sponsorships),
            valuations=list(valuations),
            operators=list(operators),
            sales=list(sales),
            expansion_fees=list(fees),
            transfers=list(transfers),
            rules=list(rules),
            net_worths=list(worths),
            stadium_costs=list(stadiums),
            staff_pay=list(staff),
            bios=list(bios),
            competitions=[{'name': 'Major League Soccer', 'abbreviation': 'MLS'}],
        )
        monkeypatch.setattr(load, 'soccer_db', db)
    return use


@pytest.mark.django_db
def test_loads_a_salary_with_its_person_team_and_competition(mongo):
    mongo([salary()], bios=[{'name': 'David Beckham', 'birthdate': datetime.datetime(1975, 5, 2),
                             'nationality': 'England'}])
    load.load()

    s = Salary.objects.select_related('person', 'team', 'competition').get()
    assert s.person.slug == 'david-beckham'
    assert s.person.birthdate == datetime.date(1975, 5, 2)
    assert s.person.nationality == 'England'
    assert s.team.slug == 'la-galaxy'
    assert s.competition.slug == 'major-league-soccer'
    assert s.competition.abbreviation == 'MLS'
    assert s.base == Decimal('5500000.08')
    assert s.guaranteed == Decimal('6500000.04')
    assert s.source == 'MLS Players Union'
    assert s.position_group == 'Midfielder'


@pytest.mark.django_db
def test_missing_team_guaranteed_and_source_stay_missing(mongo):
    mongo([salary(team=None, guaranteed=None, source=None, position='', position_group='')])
    load.load()

    s = Salary.objects.get()
    assert s.team is None
    assert s.guaranteed is None
    assert s.source == ''
    assert Team.objects.count() == 0


@pytest.mark.django_db
def test_spellings_that_share_a_slug_are_one_person(mongo):
    mongo([salary(name='Cristian Gomez', season='2006'),
           salary(name='Cristián Gómez', season='2007')])
    load.load()

    bio = Bio.objects.get()
    assert bio.slug == 'cristian-gomez'
    assert Salary.objects.filter(person=bio).count() == 2


@pytest.mark.django_db
def test_a_person_without_a_bio_on_record_still_loads(mongo):
    mongo([salary(name='Aaron Horton')])
    load.load()

    bio = Bio.objects.get()
    assert bio.birthdate is None
    assert bio.nationality == ''


@pytest.mark.django_db
def test_pay_period_is_kept(mongo):
    mongo([salary(name='Alex McNab', base='25', guaranteed=None, period='week')])
    load.load()

    assert Salary.objects.get().period == 'week'


@pytest.mark.django_db
def test_loads_sponsorships_and_their_clubs(mongo):
    mongo([salary()], sponsorships=[
        {'club': 'Toronto FC', 'competition': 'Major League Soccer', 'kind': 'stadium naming rights',
         'sponsor': 'BMO', 'property': 'BMO Field', 'start': 2007, 'end': 2016, 'length': None, 'annual': None,
         'total': 27000000, 'currency': 'CAD', 'note': 'ten years',
         'sources': ['https://a.example', 'https://b.example']},
        {'club': None, 'competition': 'Major League Soccer', 'kind': 'league sponsorship',
         'sponsor': 'Adidas', 'property': 'kit supplier', 'start': 2005, 'end': 2014, 'length': None, 'annual': None,
         'total': 150000000, 'currency': 'USD', 'note': '', 'sources': []},
    ])
    load.load()

    bmo = Sponsorship.objects.select_related('team').get(sponsor='BMO')
    assert bmo.team.slug == 'toronto-fc'      # a club with no salaries still loads
    assert bmo.currency == 'CAD'
    assert bmo.source_list() == ['https://a.example', 'https://b.example']
    assert Sponsorship.objects.get(sponsor='Adidas').team is None


@pytest.mark.django_db
def test_loads_valuations(mongo):
    mongo([salary()], valuations=[
        {'team': 'Chivas USA', 'competition': 'Major League Soccer', 'publisher': 'Forbes',
         'season': '2013', 'rank': 19, 'value': 64000000, 'revenue': 15000000,
         'operating_income': -5500000, 'published': '2013-11-20', 'revenue_season': '2012',
         'sources': ['https://a.example']},
        {'team': 'LA Galaxy', 'competition': 'Major League Soccer', 'publisher': 'Sportico',
         'season': '2021', 'rank': 2, 'value': 835000000, 'revenue': None,
         'operating_income': None, 'published': None, 'revenue_season': None, 'sources': []},
    ])
    load.load()

    chivas = Valuation.objects.select_related('team').get(publisher='Forbes')
    assert chivas.team.slug == 'chivas-usa'     # a club with no salaries still loads
    assert chivas.season == 2013 and chivas.revenue_season == 2012
    assert chivas.operating_income == -5500000
    galaxy = Valuation.objects.get(publisher='Sportico')
    assert galaxy.revenue is None and galaxy.published == '' and galaxy.revenue_season is None
    assert galaxy.team_id == Salary.objects.get().team_id


@pytest.mark.django_db
def test_loads_ownership(mongo):
    common = {'competition': 'Major League Soccer', 'note': '', 'sources': ['https://a.example']}
    mongo([salary()],
          operators=[dict(common, club='Miami Fusion', operator='Ken Horowitz', start=1997, end=2001)],
          sales=[dict(common, club='LA Galaxy', year=1998, seller='Major League Soccer',
                      buyer='Anschutz Entertainment Group', stake=None, price=26000000, valuation=None)],
          fees=[dict(common, club='Miami Fusion', awarded=1997, first_season=1998, fee=20000000)])
    load.load()

    assert Operator.objects.get().team.slug == 'miami-fusion'
    sale = Sale.objects.get()
    assert sale.price == 26000000 and sale.valuation is None and sale.stake == ''
    assert sale.team_id == Salary.objects.get().team_id
    assert ExpansionFee.objects.get().fee == 20000000


@pytest.mark.django_db
def test_loads_transfers_with_teams_only_on_the_league_side(mongo):
    base = {'competition': 'Major League Soccer', 'season': '2025', 'ceiling': None,
            'currency': 'USD', 'kind': 'transfer', 'reported': '2025-02-04', 'sources': ['https://a.example']}
    mongo([salary()], transfers=[
        {**base, 'name': 'Emmanuel Latte Lath', 'direction': 'in', 'from': 'Middlesbrough',
         'to': 'Atlanta United', 'fee': 22000000},
        {**base, 'name': 'David Beckham', 'direction': 'within', 'from': 'LA Galaxy',
         'to': 'Atlanta United', 'fee': None},
    ])
    load.load()

    t = Transfer.objects.select_related('person', 'from_team', 'to_team').get(person__slug='emmanuel-latte-lath')
    assert (t.from_name, t.from_team, t.to_team.slug, t.fee) == ('Middlesbrough', None, 'atlanta-united', 22000000)
    assert not Team.objects.filter(name='Middlesbrough').exists()
    within = Transfer.objects.get(person__slug='david-beckham')
    assert (within.from_team.slug, within.to_team.slug) == ('la-galaxy', 'atlanta-united')


@pytest.mark.django_db
def test_loads_rules_leaving_unpublished_figures_empty(mongo):
    mongo([salary()], rules=[{'competition': 'Major League Soccer', 'season': '2017',
                              'salary_budget': 3845000, 'maximum_charge': 480625,
                              'sources': ['https://a.example']}])
    load.load()

    r = Rule.objects.get()
    assert (r.season, r.salary_budget, r.maximum_charge, r.senior_minimum) == (2017, 3845000, 480625, None)


@pytest.mark.django_db
def test_loads_owners_net_worths_with_their_clubs(mongo):
    mongo([salary()], worths=[{'club': 'Atlanta United', 'owner': 'Arthur Blank', 'year': 2024,
                               'net_worth': 9200000000, 'publisher': 'Forbes', 'note': '',
                               'competition': 'Major League Soccer', 'sources': ['https://a.example']}])
    load.load()

    w = NetWorth.objects.select_related('team').get()
    assert (w.team.slug, w.owner, w.year, w.net_worth) == ('atlanta-united', 'Arthur Blank', 2024, 9200000000)


def test_owner_name_drops_the_holding_company_and_family():
    assert load.owner_name('Anthony Precourt (Two Oak Ventures)') == 'Anthony Precourt'
    assert load.owner_name('Robert Kraft and family') == 'Robert Kraft'
    assert load.owner_name('Taylor family (Carolyn Kindle) and Jim Kavanaugh') == 'Taylor family (Carolyn Kindle) and Jim Kavanaugh'


@pytest.mark.django_db
def test_operators_share_an_owner_and_net_worths_find_who_ran_the_club(mongo):
    op = {'competition': 'Major League Soccer', 'note': '', 'sources': []}
    mongo([salary()],
          operators=[{**op, 'club': 'New England Revolution', 'operator': 'Robert Kraft and family', 'start': 1995, 'end': None},
                     {**op, 'club': 'San Jose Earthquakes', 'operator': 'Robert Kraft', 'start': 1999, 'end': 2000}],
          worths=[{**op, 'club': 'New England Revolution', 'owner': 'Robert Kraft', 'year': 2024,
                   'net_worth': 11100000000, 'publisher': 'Forbes'}])
    load.load()

    kraft = Owner.objects.get()
    assert (kraft.name, kraft.slug, kraft.operator_set.count()) == ('Robert Kraft', 'robert-kraft', 2)
    assert NetWorth.objects.get().club_owner == kraft
