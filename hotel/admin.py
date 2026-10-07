from django.contrib import admin
from .models import Guest, Reservation, Room, ServiceOrder

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "room_type", "price", "status")
    list_filter = ("room_type", "status")


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email")
    search_fields = ("name", "email", "phone")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "guest", "room", "check_in", "check_out", "status")
    list_filter = ("status",)


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "guest", "service_name", "quantity", "total", "status", "timestamp")
    list_filter = ("status", "service_name")
