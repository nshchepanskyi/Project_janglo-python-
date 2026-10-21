from django.urls import path
from . import views
from .views_cbv import (
    ReservationListView,
    ReservationDetailView,
    ReservationCreateView,
    ReservationUpdateView,
    ReservationDeleteView,
    RoomListView,
    RoomDetailView,
)

app_name = 'hotel'

urlpatterns = [
    # ---------- публічний сайт ----------
    path('', views.home_view, name='home'),
    path('places/', views.places_view, name='places'),
    path('places/<str:number>/', views.place_detail_view, name='place_detail'),
    path('places/<str:number>/share/', views.share_room_view, name='share_room'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorites/toggle/<str:number>/', views.favorite_toggle_view, name='favorite_toggle'),
    path('pages/<slug:slug>/', views.page_view, name='page'),

    # ---------- auth ----------
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('logout/', views.logout_view, name='logout'),
    path('lang/', views.toggle_lang, name='toggle_lang'),
    path('theme/', views.toggle_theme, name='toggle_theme'),

    # ---------- адмін-панель ----------
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('rooms/', views.rooms_view, name='rooms'),
    path('guests/', views.guests_view, name='guests'),

    # ---------- Generic Views: бронювання (повний CRUD) (В6.1) ----------
    path('bookings/', ReservationListView.as_view(), name='booking_list'),
    path('bookings/<int:pk>/', ReservationDetailView.as_view(), name='booking_detail'),
    path('bookings/new/', ReservationCreateView.as_view(), name='booking_create'),
    path('bookings/<int:pk>/edit/', ReservationUpdateView.as_view(), name='booking_update'),
    path('bookings/<int:pk>/delete/', ReservationDeleteView.as_view(), name='booking_delete'),

    # ---------- Generic Views: номери (ListView + DetailView) ----------
    path('catalog/', RoomListView.as_view(), name='room_list'),
    path('catalog/<int:pk>/', RoomDetailView.as_view(), name='room_detail'),

    # ---------- Старі FBV-маршрути (залишаємо для сумісності) ----------
    path('reservations/', views.reservations_view, name='reservations'),
    path('reservations/<int:pk>/', views.reservation_detail_view, name='reservation_detail'),
    path('profile/', views.profile_view, name='profile'),
]
