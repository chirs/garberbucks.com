"""
Hit every URL pattern with real data from the current database and report
anything that does not return a 200. build.sh runs it before promoting a build:

    .venv/bin/python manage.py smoketest
"""

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from money.models import Salary, Transfer


class Command(BaseCommand):
    help = "GET every URL pattern with real data; fail on anything but a 200."

    def handle(self, *args, **options):
        salary = (Salary.objects.exclude(team=None).exclude(guaranteed=None)
                  .select_related('person', 'team', 'competition').order_by('-guaranteed').first())
        if salary is None:
            raise CommandError("No salaries with a team and a guaranteed figure in the database.")

        urls = [
            reverse('index'),
            reverse('pay_index'),
            reverse('clubs_index'),
            reverse('rules_index'),
            reverse('sponsorships_index'),
            reverse('valuations_index'),
            reverse('ownership_index'),
            reverse('tv_index'),
            reverse('transfers_index'),
            reverse('season_detail', args=[salary.competition.slug, salary.season]),
            reverse('team_detail', args=[salary.team.slug]),
            reverse('team_season_detail', args=[salary.team.slug, salary.season]),
            reverse('person_detail', args=[salary.person.slug]),
        ]

        # A player known only from a transfer has a page with no salaries.
        transfer = Transfer.objects.exclude(person__salary__isnull=False).select_related('person').first()
        if transfer:
            urls.append(reverse('person_detail', args=[transfer.person.slug]))

        # An owner who ran clubs in more than one league or was part of a group.
        from money.models import Owner
        urls += [o.get_absolute_url() for o in Owner.objects.all()[:3]]
        aeg = Owner.objects.filter(slug='anschutz-entertainment-group').first()
        if aeg:
            urls.append(aeg.get_absolute_url())

        # Every season page: the columns on record differ from season to season.
        seasons = Salary.objects.values_list('competition__slug', 'season').distinct()
        urls += [reverse('season_detail', args=season) for season in seasons]
        urls += [reverse('competition_detail', args=[slug]) for slug in {slug for slug, _ in seasons}]

        client = Client(headers={'host': 'localhost'})
        failures = []
        for url in dict.fromkeys(urls):
            status = client.get(url).status_code
            self.stdout.write("%s %s" % (status, url))
            if status != 200:
                failures.append(url)

        if failures:
            raise CommandError("%d of %d URLs failed" % (len(failures), len(urls)))
