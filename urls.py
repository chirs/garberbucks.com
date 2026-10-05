from django.urls import path

from money import views

urlpatterns = [
    path('', views.index, name='index'),
    path('pay/', views.pay_index, name='pay_index'),
    path('clubs/', views.clubs_index, name='clubs_index'),
    path('rules/', views.rules_index, name='rules_index'),
    path('owners/<slug:slug>/', views.owner_detail, name='owner_detail'),
    path('sponsorships/', views.sponsorships_index, name='sponsorships_index'),
    path('valuations/', views.valuations_index, name='valuations_index'),
    path('ownership/', views.ownership_index, name='ownership_index'),
    path('stadiums/', views.stadiums_index, name='stadiums_index'),
    path('tv/', views.tv_index, name='tv_index'),
    path('transfers/', views.transfers_index, name='transfers_index'),
    path('c/<slug:competition_slug>/', views.competition_detail, name='competition_detail'),
    path('c/<slug:competition_slug>/<slug:season>/', views.season_detail, name='season_detail'),
    path('teams/<slug:slug>/', views.team_detail, name='team_detail'),
    path('teams/<slug:slug>/<slug:season>/', views.team_season_detail, name='team_season_detail'),
    path('bios/<slug:slug>/', views.person_detail, name='person_detail'),
]
