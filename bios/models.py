from django.conf import settings
from django.db import models
from django.urls import reverse


class Bio(models.Model):
    """
    A person with money on record. The slug is the soccerstats.us slug.
    """

    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=200, unique=True)

    birthdate = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('person_detail', args=[self.slug])

    def soccerstats_url(self):
        return '%s/bios/%s/' % (settings.SOCCERSTATS_URL, self.slug)
