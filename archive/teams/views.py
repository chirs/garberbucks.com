import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.games.models import Game
from s2.teams.models import Team



def team_list(request):

    t = Team.objects.get(slug='united-states')
    games = Game.objects.team_filter(t)

    opponents = set([e.team1 for e in games]).union(set([e.team2 for e in games]))

    context = {
        'games': games,
        'teams': opponents,
        }

    return render_to_response("teams/list.html",
                              context,
                              context_instance=RequestContext(request))


def team_detail(request, team_id):

    t1 = Team.objects.get(slug='united-states')
    t2 = Team.objects.get(id=team_id)

    games = Game.objects.team_filter(t1, t2)

    context = {
        't1': t1,
        't2': t2,
        'games': games,
        }

    return render_to_response("teams/detail.html",
                              context,
                              context_instance=RequestContext(request))

