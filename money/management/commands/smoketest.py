"""
Hit every URL pattern with real data from the current database and report
anything that does not return a 200. build.sh runs it before promoting a build:

    .venv/bin/python manage.py smoketest
"""

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse

from money.models import Salary


class Command(BaseCommand):
    help = "GET every URL pattern with real data; fail on anything but a 200."

    def handle(self, *args, **options):
        salary = (Salary.objects.exclude(team=None).exclude(guaranteed=None)
                  .select_related('person', 'team', 'competition').order_by('-guaranteed').first())
        if salary is None:
            raise CommandError("No salaries with a team and a guaranteed figure in the database.")

        urls = [
            reverse('index'),
            reverse('season_detail', args=[salary.competition.slug, salary.season]),
            reverse('team_detail', args=[salary.team.slug]),
            reverse('team_season_detail', args=[salary.team.slug, salary.season]),
            reverse('person_detail', args=[salary.person.slug]),
        ]

        # Every season page: the columns on record differ from season to season.
        seasons = Salary.objects.values_list('competition__slug', 'season').distinct()
        urls += [reverse('season_detail', args=season) for season in seasons]

        client = Client(headers={'host': 'localhost'})
        failures = []
        for url in dict.fromkeys(urls):
            status = client.get(url).status_code
            self.stdout.write("%s %s" % (status, url))
            if status != 200:
                failures.append(url)

        if failures:
            raise CommandError("%d of %d URLs failed" % (len(failures), len(urls)))
