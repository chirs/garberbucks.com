from django.conf.urls import patterns, url

urlpatterns = patterns('stadiums.views', 
                       url(r'^$',
                           'stadium_list',
                           name='stadium_list'),

                       url(r'^(?P<stadium_id>\d+)/$',
                           'stadium_detail',
                           name='stadium_detail'),


                       )
