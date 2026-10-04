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


class Valuation(models.Model):
    """
    A team's value on a published list, as the publisher estimated it. Forbes
    values the team alone; Sportico includes its real estate and related
    businesses, so the two are not the same measure.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    publisher = models.CharField(max_length=50)
    season = models.IntegerField()

    rank = models.IntegerField()
    value = models.BigIntegerField()
    revenue = models.BigIntegerField(null=True)
    operating_income = models.BigIntegerField(null=True)

    published = models.CharField(max_length=10, blank=True) # 2018-11-14, or 2008-09
    revenue_season = models.IntegerField(null=True)
    sources = models.TextField(blank=True) # urls, one per line

    class Meta:
        ordering = ('publisher', 'season', 'rank')

    def __str__(self):
        return "%s %s: %s %s" % (self.publisher, self.season, self.team, self.value)


class Sourced(models.Model):
    """A record with a free-text note and the urls it comes from, one per line."""

    note = models.TextField(blank=True)
    sources = models.TextField(blank=True)

    class Meta:
        abstract = True

    def source_list(self):
        return self.sources.split()


class Operator(Sourced):
    """Who ran a club, and when. An empty end is the current operator."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    operator = models.CharField(max_length=300)
    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)

    class Meta:
        ordering = ('team__name', 'start')


class Sale(Sourced):
    """
    A club, or a stake in one, changing hands. Price is what was paid for the
    stake; valuation what the deal valued the whole club at.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    year = models.IntegerField()
    seller = models.CharField(max_length=300)
    buyer = models.CharField(max_length=300)
    stake = models.CharField(max_length=100, blank=True)
    price = models.BigIntegerField(null=True)
    valuation = models.BigIntegerField(null=True)

    class Meta:
        ordering = ('year', 'team__name')


class ExpansionFee(Sourced):
    """What a club paid the league to join."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    awarded = models.IntegerField()
    first_season = models.IntegerField()
    fee = models.BigIntegerField(null=True)

    class Meta:
        ordering = ('awarded', 'first_season')
