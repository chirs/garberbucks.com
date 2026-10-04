from django.conf import settings
from django.db import models
from django.urls import reverse


class Team(models.Model):
    """
    A team with money on record. The slug is the soccerstats.us slug.
    """

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('team_detail', args=[self.slug])

    def soccerstats_url(self):
        return '%s/teams/%s/' % (settings.SOCCERSTATS_URL, self.slug)
