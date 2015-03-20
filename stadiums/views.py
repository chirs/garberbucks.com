import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.games.models import Game
from s2.places.models import Stadium
from s2.teams.models import Team


def stadium_list(request):

    t = Team.objects.get(slug='united-states')
    games = Game.objects.team_filter(t)
    game_ids = set([e.stadium.id for e in games if e.stadium])
    stadiums = Stadium.objects.filter(id__in=game_ids)

    context = {
        'stadiums': stadiums,
        }

    return render_to_response("stadiums/list.html",
                              context,
                              context_instance=RequestContext(request))


def stadium_detail(request, stadium_id):

    stadium = Stadium.objects.get(id=stadium_id)

    context = {
        'stadium': stadium,
        }

    return render_to_response("stadiums/detail.html",
                              context,
                              context_instance=RequestContext(request))

