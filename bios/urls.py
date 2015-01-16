from django.conf.urls import patterns, url

urlpatterns = patterns('bios.views', 
                       url(r'^$',
                           'bio_list',
                           name='bio_list'),

                       url(r'^(?P<slug>[a-z0-9-]+)/$',
                           'bio_detail',
                           name='bio_detail'),


                       )
