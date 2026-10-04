from django.conf.urls import patterns, url

urlpatterns = patterns('home.views', 
                       url(r'^$',
                           'homepage',
                           name='homepage'),

                       )
