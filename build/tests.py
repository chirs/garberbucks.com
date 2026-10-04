import datetime
from decimal import Decimal

import pytest

from bios.models import Bio
from build import load
from money.models import Salary, Sponsorship, Valuation
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
    def use(salaries, bios=(), sponsorships=(), valuations=()):
        db = FakeDB(
            salaries=salaries,
            sponsorships=list(sponsorships),
            valuations=list(valuations),
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
         'sponsor': 'BMO', 'property': 'BMO Field', 'start': 2007, 'end': 2016, 'annual': None,
         'total': 27000000, 'currency': 'CAD', 'note': 'ten years',
         'sources': ['https://a.example', 'https://b.example']},
        {'club': None, 'competition': 'Major League Soccer', 'kind': 'league sponsorship',
         'sponsor': 'Adidas', 'property': 'kit supplier', 'start': 2005, 'end': 2014, 'annual': None,
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
