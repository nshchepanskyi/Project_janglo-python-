from django.contrib import admin
from .models import Guest, Reservation, Review, Room, RoomFavorite, Service, ServiceOrder

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "room_type", "price", "status")
    list_filter = ("room_type", "status")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Каталог послуг: додавати/редагувати позиції (назва + ціна)."""
    list_display = ("name", "price")
    search_fields = ("name",)


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email")
    search_fields = ("name", "email", "phone")


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "guest", "room", "stay_type", "check_in", "check_out", "status")
    list_filter = ("status", "stay_type")


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "guest", "service_name", "quantity", "total", "status", "timestamp")
    list_filter = ("status", "service_name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Модерація відгуків (Фаза 3): адмін бачить усі і може видаляти.

    Видалення через адмінку теж перераховує Room.rating (сигнал post_delete).
    """
    list_display = ("id", "room", "author", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("text", "room__number", "author__username")


@admin.register(RoomFavorite)
class RoomFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "room", "created_at")
    list_filter = ("room",)
