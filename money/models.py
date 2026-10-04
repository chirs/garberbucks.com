from django.db import models
from django.db.models.functions import Coalesce

from bios.models import Bio
from competitions.models import Competition
from teams.models import Team


# What a player was paid: guaranteed compensation where the source gives it,
# base salary where it does not.
PAY = Coalesce('guaranteed', 'base')


class Salary(models.Model):

    person = models.ForeignKey(Bio, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    season = models.CharField(max_length=255)

    position = models.CharField(max_length=50, blank=True)
    position_group = models.CharField(max_length=50, blank=True)

    base = models.DecimalField(max_digits=15, decimal_places=2)
    guaranteed = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    period = models.CharField(max_length=20, default='year') # year, week

    source = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=['competition', 'season'])]

    def __str__(self):
        return "%s: %s (%s)" % (self.person, self.base, self.season)


class Sponsorship(models.Model):
    """
    A deal that puts a sponsor's name on something: a stadium, a shirt, the
    league. Figures are as reported, mostly press estimates, and often missing.
    """

    NAMING_RIGHTS = 'stadium naming rights'
    SHIRT = 'front-of-shirt sponsorship'
    LEAGUE = 'league sponsorship'

    team = models.ForeignKey(Team, null=True, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    kind = models.CharField(max_length=100)

    sponsor = models.CharField(max_length=200)
    property = models.CharField(max_length=200)

    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)

    annual = models.BigIntegerField(null=True)
    total = models.BigIntegerField(null=True)
    currency = models.CharField(max_length=3, default='USD')

    note = models.TextField(blank=True)
    sources = models.TextField(blank=True) # urls, one per line

    def __str__(self):
        return "%s: %s (%s)" % (self.sponsor, self.property, self.start)

    def source_list(self):
        return self.sources.split()

    def years(self):
        if self.start and self.end:
            return '%s–%s' % (self.start, self.end) if self.start != self.end else str(self.start)
        if self.start:
            return '%s–' % self.start
        return ''
