import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.competitions.models import Competition
from s2.teams.models import Team

def competition_list(request):
    t = Team.objects.get(slug='united-states')
    #competitions = TeamStat.objects.filter(team=t).order_by('-games')
    competitions = Competition.objects.all()

    context = {
        'competitions': competitions,
        }

    return render_to_response("competitions/list.html",
                              context,
                              context_instance=RequestContext(request))


def competition_detail(request, slug):

    c = Competition.objects.get(slug=slug)
    t = Team.objects.get(slug='united-states')

    #stat = TeamStat.objects.filter(team=t).get(player=bio)
    #gs = GameStat.objects.filter(player=bio, team=t)
    #stats = Stat.objects.filter(player=bio,team=t)
    


    context = {
        'competition': c,
        }

    return render_to_response("competitions/detail.html",
                              context,
                              context_instance=RequestContext(request))


