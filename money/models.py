from django.db import models
from django.urls import reverse
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
    league. TV and streaming deals have the same shape and live here too, the
    broadcaster as sponsor and the rights as property. Figures are as reported,
    mostly press estimates, and often missing.
    """

    NAMING_RIGHTS = 'stadium naming rights'
    SHIRT = 'front-of-shirt sponsorship'
    LEAGUE = 'league sponsorship'
    NATIONAL_TV = 'national TV rights'
    LOCAL_TV = 'local TV rights'
    TV = (NATIONAL_TV, LOCAL_TV)  # media deals share the shape; pages keep them apart

    team = models.ForeignKey(Team, null=True, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    kind = models.CharField(max_length=100)

    sponsor = models.CharField(max_length=200)
    property = models.CharField(max_length=200)

    start = models.IntegerField(null=True)
    end = models.IntegerField(null=True)
    length = models.IntegerField(null=True) # contracted seasons, where it differs from start to end

    annual = models.BigIntegerField(null=True)
    total = models.BigIntegerField(null=True)
    currency = models.CharField(max_length=3, default='USD')

    note = models.TextField(blank=True)
    sources = models.TextField(blank=True) # urls, one per line

    def __str__(self):
        return "%s: %s (%s)" % (self.sponsor, self.property, self.start)

    def source_list(self):
        return self.sources.split()

    def seasons(self):
        """
        How many seasons the deal was signed for: its contracted length where
        that is on record (a deal ended early), otherwise start to end.
        """
        if self.length:
            return self.length
        if self.start and self.end:
            return self.end - self.start + 1
        return None

    def annual_inferred(self):
        """The yearly figure worked out from a reported total and length, when only the total was reported."""
        if self.annual is None and self.total is not None and self.seasons():
            return self.total / self.seasons()
        return None

    def total_inferred(self):
        """The total worked out from a reported yearly figure and length, when only the yearly figure was reported."""
        if self.total is None and self.annual is not None and self.seasons():
            return self.annual * self.seasons()
        return None

    def figure_for(self, year):
        """What the deal paid in a season it covers: the yearly figure, reported or worked out."""
        return self.annual if self.annual is not None else self.annual_inferred()

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


class Owner(models.Model):
    """
    Whoever ran a club, as the ownership record names them: a person, a family,
    a company or a group. One page each; the record's spellings of one owner
    ("Robert Kraft", "Robert Kraft and family") share it.
    """

    name = models.CharField(max_length=300, unique=True)
    slug = models.SlugField(max_length=300, unique=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('owner_detail', args=[self.slug])


class Operator(Sourced):
    """Who ran a club, and when. An empty end is the current operator."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    operator = models.CharField(max_length=300)
    owner = models.ForeignKey(Owner, null=True, on_delete=models.CASCADE)
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


class Transfer(Sourced):
    """
    A player's move into, out of or within the league, with the fee the press
    reported. Clubs on the league side are teams here, with pages; clubs
    elsewhere are names only. A bid that came to nothing is kept as a bid.
    """

    TRANSFER = 'transfer'
    ALLOCATION = 'allocation'
    BID = 'bid'

    person = models.ForeignKey(Bio, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    season = models.IntegerField()  # the first season the move affects
    direction = models.CharField(max_length=10)  # in, out or within
    kind = models.CharField(max_length=20)

    from_name = models.CharField(max_length=200, blank=True)
    to_name = models.CharField(max_length=200, blank=True)
    from_team = models.ForeignKey(Team, null=True, related_name='transfers_out', on_delete=models.CASCADE)
    to_team = models.ForeignKey(Team, null=True, related_name='transfers_in', on_delete=models.CASCADE)

    fee = models.BigIntegerField(null=True)
    ceiling = models.BigIntegerField(null=True)  # the most it can reach with add-ons
    currency = models.CharField(max_length=3, default='USD')
    reported = models.DateField(null=True)

    def __str__(self):
        return "%s: %s to %s (%s)" % (self.person, self.from_name, self.to_name, self.season)


class Rule(models.Model):
    """
    A league's roster rules for a season, as it published them: the salary
    budget each club may spend, the most one player may count against it, the
    minimum salaries, and the room beyond it. A figure the league did not
    publish, or that the rule did not yet exist for, is None.
    """

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    season = models.IntegerField()

    salary_budget = models.BigIntegerField(null=True)
    maximum_charge = models.BigIntegerField(null=True)    # the most one non-DP player counts
    senior_minimum = models.BigIntegerField(null=True)
    reserve_minimum = models.BigIntegerField(null=True)
    designated_players = models.IntegerField(null=True)   # slots per club
    general_allocation = models.BigIntegerField(null=True)   # each club's annual GAM
    targeted_allocation = models.BigIntegerField(null=True)  # each club's annual TAM
    roster = models.IntegerField(null=True)               # most players on a roster

    sources = models.TextField(blank=True)

    class Meta:
        unique_together = ('competition', 'season')

    def __str__(self):
        return "%s %s rules" % (self.competition, self.season)

    def source_list(self):
        return self.sources.split()


class NetWorth(Sourced):
    """
    What a club's owner was worth in a year, by a publisher's estimate (Forbes's
    billionaires list): the person behind the club, not the club.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    owner = models.CharField(max_length=200)  # the person, as Forbes names them
    club_owner = models.ForeignKey(Owner, null=True, on_delete=models.CASCADE)  # who ran the club that year
    year = models.IntegerField()
    net_worth = models.BigIntegerField()
    publisher = models.CharField(max_length=50)

    def __str__(self):
        return "%s %s: %s" % (self.owner, self.year, self.net_worth)
