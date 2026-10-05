import re

import pymongo

from django.db import transaction
from django.template.defaultfilters import slugify

from bios.models import Bio
from competitions.models import Competition
from money.models import ExpansionFee, NetWorth, Operator, Owner, Rule, Salary, Sale, Sponsorship, Transfer, Valuation
from teams.models import Team

# Which end of a move is a club in the league: those get team pages, the
# clubs abroad stay names.
LEAGUE_SIDE = {'in': ('to',), 'out': ('from',), 'within': ('from', 'to')}

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
    operators = list(soccer_db.operators.find())
    sales = list(soccer_db.sales.find())
    fees = list(soccer_db.expansion_fees.find())
    worths = list(soccer_db.net_worths.find())
    ownership = operators + sales + fees + worths
    transfers = list(soccer_db.transfers.find())
    rules = list(soccer_db.rules.find())

    competitions = load_competitions({e['competition'] for e in salaries + sponsorships + valuations + ownership + transfers + rules})
    teams = load_teams({e['team'] for e in salaries if e['team']} |
                       {e['club'] for e in sponsorships if e['club']} |
                       {e['team'] for e in valuations} |
                       {e['club'] for e in ownership} |
                       {e[k] for e in transfers for k in LEAGUE_SIDE[e['direction']]})
    bios = load_bios({e['name'] for e in salaries + transfers})

    load_salaries(salaries, competitions, teams, bios)
    load_sponsorships(sponsorships, competitions, teams)
    load_valuations(valuations, competitions, teams)
    load_ownership(operators, sales, fees, competitions, teams)
    load_net_worths(worths, competitions, teams, operators)
    load_transfers(transfers, competitions, teams, bios)
    load_rules(rules, competitions)


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
            coverage=e.get('coverage') or 'full',
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
            length=e['length'],
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


def owner_name(operator):
    """
    The owner an operator record names, without the holding company in
    parentheses or a trailing "and family": "Anthony Precourt (Two Oak
    Ventures)" and "Anthony Precourt (Precourt Sports Ventures)" are one owner.
    """
    name = re.sub(r'\s*\([^()]*\)$', '', operator)
    return re.sub(r' and family$', '', name)


def load_ownership(operators, sales, fees, competitions, teams):
    print("loading {} operators, {} sales, {} expansion fees".format(len(operators), len(sales), len(fees)))

    names = sorted({owner_name(e['operator']) for e in operators})
    owners = {o.name: o.id for o in Owner.objects.bulk_create(Owner(name=n, slug=slugify(n)) for n in names)}

    def common(e):
        return {'team_id': teams[e['club']], 'competition_id': competitions[e['competition']],
                'note': e['note'], 'sources': '\n'.join(e['sources'])}

    Operator.objects.bulk_create(
        Operator(operator=e['operator'], owner_id=owners[owner_name(e['operator'])],
                 start=e['start'], end=e['end'], **common(e))
        for e in operators)
    Sale.objects.bulk_create(
        Sale(year=e['year'], seller=e['seller'], buyer=e['buyer'], stake=e['stake'] or '',
             price=e['price'], valuation=e['valuation'], **common(e))
        for e in sales)
    ExpansionFee.objects.bulk_create(
        ExpansionFee(awarded=e['awarded'], first_season=e['first_season'], fee=e['fee'], **common(e))
        for e in fees)


def load_net_worths(worths, competitions, teams, operators):
    print("loading {} owners' net worths".format(len(worths)))

    owners = {o.name: o.id for o in Owner.objects.all()}

    def running(club, year):
        """Who ran the club that year: of the operators covering it, the one who took over last."""
        spans = [o for o in operators if o['club'] == club and (o['start'] or 0) <= year <= (o['end'] or year)]
        latest = max(spans, key=lambda o: o['start'] or 0, default=None)
        return owners.get(owner_name(latest['operator'])) if latest else None

    NetWorth.objects.bulk_create(
        NetWorth(team_id=teams[e['club']], competition_id=competitions[e['competition']],
                 owner=e['owner'], club_owner_id=running(e['club'], e['year']),
                 year=e['year'], net_worth=e['net_worth'], publisher=e['publisher'],
                 note=e['note'], sources='\n'.join(e['sources']))
        for e in worths)


def load_transfers(transfers, competitions, teams, bios):
    print("loading {} transfers".format(len(transfers)))

    def team(e, end):
        return teams[e[end]] if end in LEAGUE_SIDE[e['direction']] and e[end] else None

    Transfer.objects.bulk_create(
        Transfer(
            person_id=bios[slugify(e['name'])],
            competition_id=competitions[e['competition']],
            season=int(e['season']),
            direction=e['direction'],
            kind=e['kind'],
            from_name=e['from'],
            to_name=e['to'],
            from_team_id=team(e, 'from'),
            to_team_id=team(e, 'to'),
            fee=e['fee'],
            ceiling=e['ceiling'],
            currency=e['currency'],
            reported=e['reported'],
            sources='\n'.join(e['sources']),
            )
        for e in transfers)


RULE_FIELDS = ('salary_budget', 'maximum_charge', 'senior_minimum', 'reserve_minimum',
               'designated_players', 'general_allocation', 'targeted_allocation', 'roster')


def load_rules(rules, competitions):
    print("loading {} seasons of rules".format(len(rules)))

    Rule.objects.bulk_create(
        Rule(
            competition_id=competitions[e['competition']],
            season=int(e['season']),
            sources='\n'.join(e['sources']),
            **{k: e.get(k) for k in RULE_FIELDS},
            )
        for e in rules)
