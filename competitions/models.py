from django.db import models


class Competition(models.Model):
    """
    A competition with money on record. The slug is the soccerstats.us slug.
    """

    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=15, blank=True)
    slug = models.SlugField(max_length=150, unique=True)

    def __str__(self):
        return self.name
