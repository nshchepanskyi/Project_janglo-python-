from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('places/', views.places_view, name='places'),
    path('places/<str:number>/', views.place_detail_view, name='place_detail'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorites/toggle/<str:number>/', views.favorite_toggle_view, name='favorite_toggle'),
    path('pages/<slug:slug>/', views.page_view, name='page'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('lang/', views.toggle_lang, name='toggle_lang'),
    path('theme/', views.toggle_theme, name='toggle_theme'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('rooms/', views.rooms_view, name='rooms'),
    path('reservations/', views.reservations_view, name='reservations'),
    path('reservations/<int:pk>/', views.reservation_detail_view, name='reservation_detail'),
    path('guests/', views.guests_view, name='guests'),
    path('profile/', views.profile_view, name='profile'),
]
