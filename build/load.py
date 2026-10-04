import pymongo

from django.db import transaction
from django.template.defaultfilters import slugify

from bios.models import Bio
from competitions.models import Competition
from money.models import Salary, Sponsorship, Valuation
from teams.models import Team

connection = pymongo.MongoClient()
soccer_db = connection.soccer


@transaction.atomic
def load():
    """
    Load the money data and only the people, teams and competitions it names.
    Everything else about them stays on soccerstats.us, reached by slug.
    """
    salaries = list(soccer_db.salaries.find())
    sponsorships = list(soccer_db.sponsorships.find())
    valuations = list(soccer_db.valuations.find())

    competitions = load_competitions({e['competition'] for e in salaries + sponsorships + valuations})
    teams = load_teams({e['team'] for e in salaries if e['team']} |
                       {e['club'] for e in sponsorships if e['club']} |
                       {e['team'] for e in valuations})
    bios = load_bios({e['name'] for e in salaries})

    load_salaries(salaries, competitions, teams, bios)
    load_sponsorships(sponsorships, competitions, teams)
    load_valuations(valuations, competitions, teams)


def load_competitions(names):
    print("loading {} competitions".format(len(names)))

    abbreviations = {e['name']: e.get('abbreviation') or ''
                     for e in soccer_db.competitions.find({'name': {'$in': sorted(names)}})}

    competitions = Competition.objects.bulk_create(
        Competition(name=name, slug=slugify(name), abbreviation=abbreviations.get(name, ''))
        for name in sorted(names))
    return {e.name: e.id for e in competitions}


def load_teams(names):
    print("loading {} teams".format(len(names)))

    teams = Team.objects.bulk_create(
        Team(name=name, slug=slugify(name)) for name in sorted(names))
    return {e.name: e.id for e in teams}


def load_bios(names):
    """
    One bio per slug, so two spellings that soccerstats.us serves on one page
    (Cristian Gomez, Cristián Gómez) are one person here too.
    """
    print("loading {} bios".format(len(names)))

    details = {e['name']: e for e in soccer_db.bios.find({'name': {'$in': sorted(names)}})}

    by_slug = {}
    for name in sorted(names):
        by_slug.setdefault(slugify(name), name)

    bios = []
    for slug, name in by_slug.items():
        d = details.get(name, {})
        bios.append(Bio(
            name=name,
            slug=slug,
            birthdate=d.get('birthdate') or None,
            nationality=d.get('nationality') or '',
            ))

    return {e.slug: e.id for e in Bio.objects.bulk_create(bios)}


def load_salaries(salaries, competitions, teams, bios):
    print("loading {} salaries".format(len(salaries)))

    Salary.objects.bulk_create(
        Salary(
            person_id=bios[slugify(e['name'])],
            team_id=teams[e['team']] if e['team'] else None,
            competition_id=competitions[e['competition']],
            season=e['season'],
            position=e['position'],
            position_group=e['position_group'],
            base=e['base'],
            guaranteed=e['guaranteed'],
            period=e['period'],
            source=e['source'] or '',
            )
        for e in salaries)


def load_sponsorships(sponsorships, competitions, teams):
    print("loading {} sponsorships".format(len(sponsorships)))

    Sponsorship.objects.bulk_create(
        Sponsorship(
            team_id=teams[e['club']] if e['club'] else None,
            competition_id=competitions[e['competition']],
            kind=e['kind'],
            sponsor=e['sponsor'],
            property=e['property'],
            start=e['start'],
            end=e['end'],
            annual=e['annual'],
            total=e['total'],
            currency=e['currency'] or 'USD',
            note=e['note'],
            sources='\n'.join(e['sources']),
            )
        for e in sponsorships)


def load_valuations(valuations, competitions, teams):
    print("loading {} valuations".format(len(valuations)))

    Valuation.objects.bulk_create(
        Valuation(
            team_id=teams[e['team']],
            competition_id=competitions[e['competition']],
            publisher=e['publisher'],
            season=int(e['season']),
            rank=e['rank'],
            value=e['value'],
            revenue=e['revenue'],
            operating_income=e['operating_income'],
            published=e['published'] or '',
            revenue_season=int(e['revenue_season']) if e['revenue_season'] else None,
            sources='\n'.join(e['sources']),
            )
        for e in valuations)
