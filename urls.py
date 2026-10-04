from django.urls import path

from money import views

urlpatterns = [
    path('', views.index, name='index'),
    path('c/<slug:competition_slug>/', views.competition_detail, name='competition_detail'),
    path('c/<slug:competition_slug>/<slug:season>/', views.season_detail, name='season_detail'),
    path('teams/<slug:slug>/', views.team_detail, name='team_detail'),
    path('teams/<slug:slug>/<slug:season>/', views.team_season_detail, name='team_season_detail'),
    path('bios/<slug:slug>/', views.person_detail, name='person_detail'),
]
