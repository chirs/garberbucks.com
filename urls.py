from django.conf.urls import url, include, patterns
#from django.conf.urls.defaults import url, include, patterns                                                                                                                        

from django.contrib import admin
from django.views.generic import RedirectView, TemplateView

admin.autodiscover()



urlpatterns = patterns('',

                       url(r'^$', include('home.urls')),
                       url(r'^games/', include('games.urls')),
                       url(r'^stats/', include('stats.urls')),
                       url(r'^bios/', include('bios.urls')),
                       url(r'^teams/', include('teams.urls')),
                       url(r'^stadiums/', include('stadiums.urls')),

                       #url(r"^$", "home.homepage", name="homepage"),

                       #url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),                                                                     

                       url(r'^favicon\.ico$', RedirectView.as_view(url='http://media.socceroutsider.com/images/favicon.ico'), name="favicon"),
                       url(r'^robots.txt$', RedirectView.as_view(url='http://media.socceroutsider.com/robots.txt'), name="robots.txt"),

                       #url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),


                       #(r'^api/$', TemplateView.as_view(template_name='api.html'), name='api'),                                                                                     
                       #(r'^sources/$', direct_to_template, {'template': 'sources.html'}),                                                                                           
                       #(r'^blog/$', direct_to_template, {'template': 'blog.html'}),                                                                                                 

                       #url(r'search/',
                       #    SearchView(load_all=False, searchqueryset=sqs),
                       #    name='haystack_search',
                       #    ),
                       #include('haystack.urls')),                                                                                                                                   


                       #    url(r"^calendar/$", "dates.views.calendar", name="calendar_index"),
                       )
