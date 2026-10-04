import datetime
from decimal import Decimal

import pytest

from bios.models import Bio
from build import load
from money.models import Salary
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
    e = {'name': 'David Beckham', 'team': 'LA Galaxy', 'position': 'M',
         'base': '5500000.08', 'guaranteed': '6500000.04',
         'competition': 'Major League Soccer', 'season': '2007',
         'source': 'MLS Players Union', 'period': 'year'}
    e.update(kw)
    return e


@pytest.fixture
def mongo(monkeypatch):
    def use(salaries, bios=()):
        db = FakeDB(
            salaries=salaries,
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


@pytest.mark.django_db
def test_missing_team_guaranteed_and_source_stay_missing(mongo):
    mongo([salary(team=None, guaranteed=None, source=None, position='')])
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
