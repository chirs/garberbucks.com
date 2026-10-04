import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page

from s2.games.models import Game
from s2.teams.models import Team



def game_list(request):
    t = Team.objects.get(slug='united-states')
    games = Game.objects.team_filter(t)

    context = {
        'games': games,
        }

    return render_to_response("games/list.html",
                              context,
                              context_instance=RequestContext(request))


def game_detail(request, game_id):

    game = Game.objects.get(id=game_id)

    context = {
        'game': game,
        }

    return render_to_response("games/detail.html",
                              context,
                              context_instance=RequestContext(request))

