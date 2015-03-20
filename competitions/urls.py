from django.conf.urls import patterns, url

urlpatterns = patterns('competitions.views', 
                       url(r'^$',
                           'competition_list',
                           name='competition_list'),

                       url(r'^(?P<slug>[a-z0-9-]+)/$',
                           'competition_detail',
                           name='competition_detail'),


                       )
