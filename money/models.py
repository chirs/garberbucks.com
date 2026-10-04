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

    position = models.CharField(max_length=20, blank=True)

    base = models.DecimalField(max_digits=15, decimal_places=2)
    guaranteed = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    period = models.CharField(max_length=20, default='year') # year, week

    source = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=['competition', 'season'])]

    def __str__(self):
        return "%s: %s (%s)" % (self.person, self.base, self.season)
