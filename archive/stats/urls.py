from django.conf.urls import patterns, url

urlpatterns = patterns('stats.views', 
                       url(r'^$',
                           'stat_list',
                           name='stat_list'),

                       url(r'^(?P<stat_id>\d+)/$',
                           'stat_detail',
                           name='stat_detail'),

                       )
