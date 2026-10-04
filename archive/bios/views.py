import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.bios.models import Bio
from s2.teams.models import Team
from s2.stats.models import GameStat, TeamStat, Stat


def bio_list(request):
    t = Team.objects.get(slug='united-states')
    stats = TeamStat.objects.filter(team=t).order_by('-games')

    context = {
        'stats': stats,
        }

    return render_to_response("bios/list.html",
                              context,
                              context_instance=RequestContext(request))


def bio_detail(request, slug):

    bio = Bio.objects.get(slug=slug)
    t = Team.objects.get(slug='united-states')

    stat = TeamStat.objects.filter(team=t).get(player=bio)
    gs = GameStat.objects.filter(player=bio, team=t)

    stats = Stat.objects.filter(player=bio,team=t)
    


    context = {
        'bio': bio,
        'stat': stat,
        'gs': gs,
        'stats': stats,
        }

    return render_to_response("bios/detail.html",
                              context,
                              context_instance=RequestContext(request))


