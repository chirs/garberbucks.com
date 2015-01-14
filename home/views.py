import datetime

from django.db import models
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import cache_page


from collections import defaultdict, Counter
import json



def homepage(request):
    
    #try:
    #    mls = Competition.objects.get(slug='major-league-soccer')
    #except:
    #    mls = None

    mls = None

    context = {
        'mls': mls,
        }

    return render_to_response("homepage.html",
                              context,
                              context_instance=RequestContext(request))
        
