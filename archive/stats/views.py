import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.stats.models import TeamStat, Stat
from s2.teams.models import Team


def stat_list(request):
    t = Team.objects.get(slug='united-states')
    stats = TeamStat.objects.filter(team=t).order_by('-games_played')

    context = {
        'stats': stats,
        }

    return render_to_response("stats/list.html",
                              context,
                              context_instance=RequestContext(request))


def stat_detail(request, stat_id):

    stat = Stat.objects.get(id=stat_id)

    context = {
        'stat': stat,
        }

    return render_to_response("stats/detail.html",
                              context,
                              context_instance=RequestContext(request))


