from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Sum
from django.utils import timezone


ROOM_TYPES = [
    ("Single", "Single"),
    ("Double", "Double"),
    ("Suite", "Suite"),
]

ROOM_STATUSES = [
    ("Available", "Available"),
    ("Occupied", "Occupied"),
    ("Cleaning", "Cleaning"),
    ("Maintenance", "Maintenance"),
]

RESERVATION_STATUSES = [
    ("Pending", "Pending"),
    ("Checked-In", "Checked-In"),
    ("Checked-Out", "Checked-Out"),
]

SERVICE_ORDER_STATUSES = [
    ("Pending", "Pending"),
    ("In Progress", "In Progress"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]

# Port of SERVICES_CATALOG from Flet version (hotel_data.py)
SERVICES_CATALOG = [
    {"name": "Breakfast", "price": Decimal("10")},
    {"name": "Laundry", "price": Decimal("15")},
    {"name": "Spa", "price": Decimal("50")},
    {"name": "Airport Transfer", "price": Decimal("25")},
    {"name": "Gym", "price": Decimal("20")},
    {"name": "Pool", "price": Decimal("15")},
    {"name": "Parking", "price": Decimal("12")},
    {"name": "Room Service", "price": Decimal("8")},
    {"name": "Mini Bar", "price": Decimal("18")},
    {"name": "Dry Cleaning", "price": Decimal("22")},
    {"name": "Conference Room", "price": Decimal("100")},
    {"name": "Movie Rental", "price": Decimal("12")},
    {"name": "Bicycle Rental", "price": Decimal("30")},
]

SERVICE_PRICES = {s["name"]: s["price"] for s in SERVICES_CATALOG}


class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="Single")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ROOM_STATUSES, default="Available")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Room {self.number} ({self.status})"

    def clean(self):
        if self.price is not None and self.price < 0:
            raise ValidationError("Price cannot be negative")


class Guest(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.pk})"


class Reservation(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name="reservations")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="reservations")
    # Хто створив бронювання: для звичайного користувача — він сам
    # (його записи видно лише в його профілі); NULL для записів, створених
    # до запровадження ролей. Адмін бачить усі записи незалежно від поля.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reservations",
    )
    check_in = models.DateField()
    check_out = models.DateField()
    status = models.CharField(max_length=20, choices=RESERVATION_STATUSES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"R{self.pk} {self.guest.name} -> {self.room.number}"

    def clean(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError("Check out must be later than check in")

    @property
    def nights(self):
        try:
            return max((self.check_out - self.check_in).days, 1)
        except Exception:
            return 1

    @property
    def amount(self):
        return self.room.price * self.nights


class ServiceOrder(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name="service_orders")
    service_name = models.CharField(max_length=50)
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=SERVICE_ORDER_STATUSES, default="Pending")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.pk} {self.service_name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.total = self.service_price * self.quantity
        super().save(*args, **kwargs)


# Business-logic helpers (ported from hotel_data.py calc_*/get_*)

def calc_reservation_revenue():
    total = Decimal("0")
    for r in Reservation.objects.select_related("room").all():
        total += r.amount
    return total


def calc_service_revenue():
    return ServiceOrder.objects.aggregate(s=Sum("total"))["s"] or Decimal("0")


def calc_total_revenue():
    return calc_reservation_revenue() + calc_service_revenue()


def get_occupancy_rate():
    total = Room.objects.count()
    if not total:
        return 0
    occupied = Room.objects.filter(status="Occupied").count()
    return round(occupied / total * 100)


def get_services_summary(limit=5):
    qs = (
        ServiceOrder.objects.values("service_name")
        .annotate(count=Sum("quantity"), revenue=Sum("total"))
        .order_by("-revenue")[:limit]
    )
    return [{"name": r["service_name"], "count": r["count"], "revenue": r["revenue"]} for r in qs]


def arrivals_count():
    today = timezone.localdate()
    by_date = Reservation.objects.filter(check_in=today).count()
    # Flet version counted Pending/Checked-In as "arrivals"; keep both metrics
    active = Reservation.objects.filter(status__in=["Pending", "Checked-In"]).count()
    checked_in = Reservation.objects.filter(status="Checked-In").count()
    return {"today": by_date, "active": active, "checked_in": checked_in}
