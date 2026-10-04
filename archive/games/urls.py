from django.conf.urls import patterns, url

urlpatterns = patterns('games.views', 
                       url(r'^$',
                           'game_list',
                           name='game_list'),

                       url(r'^(?P<game_id>\d+)/$',
                           'game_detail',
                           name='game_detail'),


                       )
