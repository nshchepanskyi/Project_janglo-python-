from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count, Q, Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


ROOM_TYPES = [
    ("Single", "Single"),
    ("Double", "Double"),
    ("Suite", "Suite"),
]

# Ліміт місткості за типом номера: одномісний → 1 гість, двомісний → 2,
# люкс → максимум 8. Правило використовують Room.clean() (адмінка /admin/),
# Reservation.clean() і форма «Add Room» у панелі керування.
ROOM_CAPACITY_LIMITS = {
    "Single": 1,
    "Double": 2,
    "Suite": 8,
}

# Глобальний максимум гостей (величезний Suite): поле Guests на публічному
# сайті обмежене цим значенням.
MAX_GUESTS = max(ROOM_CAPACITY_LIMITS.values())

# Статичні (перекладувані) тексти помилок перевірки місткості
CAPACITY_ERRORS = {
    "Single": "A Single room fits 1 guest",
    "Double": "A Double room fits 2 guests",
    "Suite": "A Suite room fits up to 8 guests",
}


def capacity_error(room_type, capacity):
    """Помилка місткості за типом номера або None, якщо все в межах ліміту."""
    limit = ROOM_CAPACITY_LIMITS.get(room_type)
    if limit is None or capacity is None:
        return None
    if capacity < 1:
        return "Capacity must be at least 1"
    if capacity > limit:
        return CAPACITY_ERRORS[room_type]
    return None

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

# Тип перебування: Night — класичний нічліг (заїзд → виїзд наступного дня),
# Day — денне бронювання: гість приїхав зранку (наприклад, на зустріч увечері)
# і хоче відпочити в номері лише на день, без ночівлі.
STAY_NIGHT, STAY_DAY = "Night", "Day"
STAY_TYPES = [
    (STAY_NIGHT, "Night"),
    (STAY_DAY, "Day"),
]

# Фіксовані години денного бронювання: заїзд о 07:00, виїзд о 23:59
# («з 7am до 12am») того самого дня. У базі зберігається одна дата —
# check_in == check_out.
DAY_CHECK_IN_TIME = "07:00"
DAY_CHECK_OUT_TIME = "23:59"

SERVICE_ORDER_STATUSES = [
    ("Pending", "Pending"),
    ("In Progress", "In Progress"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]

# Початкові дані каталогу послуг (порт SERVICES_CATALOG з Flet hotel_data.py).
# У базі це таблиця hotel_service (модель Service) — список лише наповнює її
# під час міграції та слугує довідкою для hotel/sql/02_seed.sql.
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

# Сервісний збір публічного бронювання: 12% від суми за ночі,
# округлено до цілих доларів — саме так, як на макеті ($120 + $14 = $134).
SERVICE_FEE_RATE = Decimal("0.12")


def calc_service_fee(subtotal):
    if not subtotal:
        return Decimal("0")
    return (subtotal * SERVICE_FEE_RATE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class Service(models.Model):
    """
    Каталог послуг у базі даних (замість жорстко закодованого SERVICES_CATALOG).

    Дві ролі:
    - при створенні номера адміністратор ставить галочки «що є в цьому номері»
      (Room.services) — ці послуги показуються на картці та в списку номерів;
    - під час проживання гість додає додаткові послуги до свого бронювання
      (ServiceOrder) і оплачує їх перед виселенням.
    Додавати/редагувати позиції каталогу можна в /admin/ (або міграцією).
    """

    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (${self.price})"


class Room(models.Model):
    number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="Single")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ROOM_STATUSES, default="Available")

    # Публічна картка (Фаза 1): назва, локація, місткість, рейтинг, фото.
    # Фото вантажиться у media/rooms/ (FileField); якщо порожньо — плейсхолдер «Фото».
    title = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=120, blank=True, default="")
    capacity = models.PositiveIntegerField(default=2)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("4.5"))
    photo = models.ImageField(upload_to="rooms/", blank=True)
    # «Що є в цьому номері» — галочки з каталогу послуг при додаванні номера
    services = models.ManyToManyField(Service, blank=True, related_name="rooms")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Room {self.number} ({self.status})"

    def clean(self):
        if self.price is not None and self.price < 0:
            raise ValidationError("Price cannot be negative")
        err = capacity_error(self.room_type, self.capacity)
        if err:
            raise ValidationError({"capacity": err})

    @property
    def display_title(self):
        """Назва для публічної картки: якщо не задано — «Room 101»."""
        return self.title or f"Room {self.number}"


class Guest(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.pk})"


def conflict_q(check_in, check_out, stay_type=STAY_NIGHT):
    """Q-фільтр активних бронювань, що перетинаються з бажаним інтервалом.

    Нічліг [ci, co) конфліктує з нічлігом лише на справжньому перетині
    (сусідні дати — заїзд у день виїзду — дозволені). Денне бронювання
    займає ВЕСЬ день D (07:00 → 23:59), тому:
    - день D конфліктує з нічлігом [ci, co] включно з обома межами
      (гість нічлігу заїжджає того вечора, а виїжджає вранці дня D);
    - нічліг конфліктує з усіма днями, що потрапили в [ci, co];
    - день із днем — лише на рівну дату.
    """
    if stay_type == STAY_DAY:
        return (
            Q(stay_type=STAY_NIGHT, check_in__lte=check_in, check_out__gte=check_in)
            | Q(stay_type=STAY_DAY, check_in=check_in)
        )
    return (
        Q(stay_type=STAY_NIGHT, check_in__lt=check_out, check_out__gt=check_in)
        | Q(stay_type=STAY_DAY, check_in__gte=check_in, check_in__lte=check_out)
    )


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
    # Скільки гостей заселяється (для публічного пошуку/картки місця)
    guests = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=RESERVATION_STATUSES, default="Pending")
    # Тип перебування: Night — нічліг (заїзд → виїзд наступного дня),
    # Day — денне бронювання: 07:00 → 23:59 того самого дня (без ночівлі).
    # Для Day у базі зберігається одна дата: check_in == check_out.
    stay_type = models.CharField(max_length=10, choices=STAY_TYPES, default=STAY_NIGHT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"R{self.pk} {self.guest.name} -> {self.room.number}"

    def clean(self):
        if self.stay_type == STAY_DAY:
            # Денне бронювання: одна й та сама дата, години 07:00 → 23:59
            if self.check_in and self.check_out and self.check_out != self.check_in:
                raise ValidationError("A day stay is one day only")
        elif self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError("Check out must be later than check in")
        # Накладання дат: активне бронювання цього номера перетинається з новим.
        # Сусідні дати нічлігу (заїзд у день виїзду) дозволені — перетину немає;
        # день конфліктує з нічлігом на обох межах (07:00–23:59 — увесь день).
        if self.room_id and self.check_in and self.check_out:
            clash = (
                Reservation.objects.filter(
                    room_id=self.room_id,
                    status__in=ACTIVE_STATUSES,
                )
                .filter(conflict_q(self.check_in, self.check_out, self.stay_type))
                .exclude(pk=self.pk)
            )
            if clash.exists():
                raise ValidationError(
                    "This room is already booked for the selected dates"
                )
        # Не більше гостей, ніж вміщує тип номера (Single 1, Double 2, Suite 8)
        if self.room_id and self.guests:
            err = capacity_error(self.room.room_type, self.guests)
            if err:
                raise ValidationError({"guests": err})

    @property
    def is_day_use(self):
        """Денне бронювання (07:00 → 23:59, без ночівлі)."""
        return self.stay_type == STAY_DAY

    @property
    def nights(self):
        """Кількість ночей; для денного бронювання — 0 (ночівлі немає)."""
        try:
            n = (self.check_out - self.check_in).days
        except Exception:
            n = 1
        return 0 if self.is_day_use else max(n, 1)

    @property
    def days(self):
        """Одиниць оплати: 1 день для денного бронювання, інакше — ночі."""
        return 1 if self.is_day_use else self.nights

    @property
    def check_in_time(self):
        """Година заїзду (лише для дня: 07:00)."""
        return DAY_CHECK_IN_TIME if self.is_day_use else ""

    @property
    def check_out_time(self):
        """Година виїзду (лише для дня: 23:59)."""
        return DAY_CHECK_OUT_TIME if self.is_day_use else ""

    @property
    def amount(self):
        return self.room.price * self.days

    @property
    def fee(self):
        return calc_service_fee(self.amount)

    @property
    def total(self):
        return self.amount + self.fee

    @property
    def extras_total(self):
        """Додаткові послуги, замовлені під час проживання (без скасованих)."""
        qs = self.service_orders.exclude(status="Cancelled")
        return sum((o.total for o in qs), start=Decimal("0"))

    @property
    def extras_due(self):
        """Скільки треба сплатити перед виселенням (неоплачені послуги)."""
        qs = self.service_orders.filter(paid=False).exclude(status="Cancelled")
        return sum((o.total for o in qs), start=Decimal("0"))


class ServiceOrder(models.Model):
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name="service_orders")
    # До якого бронювання належить послуга (для рахунку «перед виселенням»).
    # NULL — записи, створені до цього поля (зберігаємо історію).
    reservation = models.ForeignKey(
        Reservation, null=True, blank=True,
        on_delete=models.CASCADE, related_name="service_orders",
    )
    service_name = models.CharField(max_length=50)
    service_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=SERVICE_ORDER_STATUSES, default="Pending")
    # Оплата: гість сплачує додаткові послуги перед виселенням
    paid = models.BooleanField(default=False)

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


# ---------- публічний пошук (Фаза 1) ----------

ACTIVE_STATUSES = ["Pending", "Checked-In"]


def search_rooms(location="", check_in=None, check_out=None, guests=None, stay_type=STAY_NIGHT):
    """
    Пошук місць для публічного каталогу.

    - location  — збіг у назві, локації або номері;
    - guests    — лише номери з місткістю не меншою за кількість гостей;
    - дати      — головне правило: номер вільний, якщо жодне активне бронювання
                  не перетинається з бажаним інтервалом (див. conflict_q):
                  нічліг ↔ нічліг на напіввідкритому інтервалі
                  (new.check_in < other.check_out AND new.check_out > other.check_in),
                  а день (07:00–23:59) займає весь календарний день.
    - stay_type — тип бажаного перебування: для дня достатньо лише check_in
                  (check_out не потрібен — він дорівнює check_in).
    """
    qs = Room.objects.all()
    if location:
        qs = qs.filter(
            Q(title__icontains=location)
            | Q(location__icontains=location)
            | Q(number__icontains=location)
        )
    if guests:
        qs = qs.filter(capacity__gte=guests)
    if check_in and (check_out or stay_type == STAY_DAY):
        busy = (
            Reservation.objects.filter(status__in=ACTIVE_STATUSES)
            .filter(conflict_q(check_in, check_out, stay_type))
            .values_list("room_id", flat=True)
        )
        qs = qs.exclude(pk__in=busy)
    return qs


def room_is_free(room, check_in=None, check_out=None, stay_type=STAY_NIGHT):
    """Чи вільний номер: за датами — перевірка перетину, без дат — статус.

    Для денного бронювання (stay_type=Day) достатньо лише check_in —
    номер зайнятий на весь день D, якщо є нічліг, що накриває D
    (включно з межами), або інший день D.
    """
    if stay_type == STAY_DAY:
        if not check_in:
            return room.status == "Available"
        return not (
            Reservation.objects.filter(room=room, status__in=ACTIVE_STATUSES)
            .filter(conflict_q(check_in, None, STAY_DAY))
            .exists()
        )
    if not (check_in and check_out):
        return room.status == "Available"
    return not (
        Reservation.objects.filter(room=room, status__in=ACTIVE_STATUSES)
        .filter(conflict_q(check_in, check_out, STAY_NIGHT))
        .exists()
    )


# ---------- Фаза 3: обране + відгуки (персоналізація гостя) ----------

def recalc_room_rating(room):
    """Середня оцінка живих відгуків перетікає в Room.rating.

    Поки відгуків немає — rating лишається початковим (seed із 02_seed.sql).
    Викликається зі сигналів post_save/post_delete, тому видалення відгуку
    в /admin/ теж перераховує зірочки на картках.
    """
    avg = room.reviews.aggregate(v=Avg("rating"))["v"]
    if avg is None:
        return
    room.rating = Decimal(str(round(avg, 1)))
    room.save(update_fields=["rating"])


class RoomFavorite(models.Model):
    """Обране: користувач ↔ номер (зірочка на картці та сторінці місця).

    Кілька кліків по зірочці — toggle (у views.favorite_toggle_view).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_rooms",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "room")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} ★ {self.room.number}"


class Review(models.Model):
    """Відгук гостя, який реально жив у номері.

    Чесна схема: писати можна лише ПІСЛЯ виселення (Checked-Out) з цього
    саме номера і лише одне повідомлення на бронювання (OneToOneField) —
    див. hotel/views.py `_create_review`. Середня оцінка перетікає
    в Room.rating через recalc_room_rating (зірочки на картках «живі»).
    """

    RATING_MIN, RATING_MAX = 1, 5

    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE, related_name="review",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.room.number} ★{self.rating} ({self.author.username})"

    def clean(self):
        if self.rating is not None and not (self.RATING_MIN <= self.rating <= self.RATING_MAX):
            raise ValidationError({"rating": "Rating must be between 1 and 5"})


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def _review_rating_recalc(sender, instance, **kwargs):
    """Збереження/видалення відгуку одразу оновлює Room.rating."""
    recalc_room_rating(instance.room)
