from django.conf.urls import patterns, url

urlpatterns = patterns('teams.views', 
                       url(r'^$',
                           'team_list',
                           name='team_list'),

                       url(r'^(?P<team_id>\d+)/$',
                           'team_detail',
                           name='team_detail'),


                       )
