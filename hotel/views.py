import re
from datetime import date
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Guest,
    MAX_GUESTS,
    ROOM_CAPACITY_LIMITS,
    Reservation,
    Room,
    Service,
    ServiceOrder,
    arrivals_count,
    calc_reservation_revenue,
    calc_service_fee,
    calc_service_revenue,
    calc_total_revenue,
    capacity_error,
    get_occupancy_rate,
    get_services_summary,
    room_is_free,
    search_rooms,
)


def _lang(request):
    return request.session.get("lang", "en")


# ---------- roles: admin (staff) vs regular user ----------

def is_admin(user):
    """Адміністратор = персонал/суперкористувач (керує всім функціоналом)."""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def home_redirect(user):
    """Куди відправляти після входу/реєстрації."""
    return "dashboard" if is_admin(user) else "profile"


def admin_required(view_func):
    """Лише для адміністратора; звичайний користувач потрапляє у профіль."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Access restricted to administrators")
            return redirect("profile")
        return view_func(request, *args, **kwargs)
    return login_required(wrapper)


# ---------- auth (port of auth.py: validate_* + register_user + login_user) ----------

def _validate_username(username):
    return isinstance(username, str) and len(username.strip()) >= 3


def _validate_password(password):
    return isinstance(password, str) and len(password) >= 6


def _validate_email(email):
    try:
        django_validate_email(email)
        return True
    except ValidationError:
        return False


def register_view(request):
    if request.user.is_authenticated:
        return redirect(home_redirect(request.user))
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")
        if not _validate_username(username):
            messages.error(request, "Username must contain at least 3 characters")
        elif not _validate_email(email):
            messages.error(request, "Invalid email")
        elif not _validate_password(password):
            messages.error(request, "Password must contain at least 6 characters")
        elif password != confirm:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Registration successful")
            return redirect("login")
    return render(request, "hotel/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_redirect(request.user))
    if request.method == "POST":
        login_input = request.POST.get("login", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=login_input, password=password)
        if user is None:
            # allow login by email (port of login_user which accepts username OR email)
            try:
                u = User.objects.get(email=login_input)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is None:
            messages.error(request, "Invalid credentials")
        else:
            login(request, user)
            # Повернення на сторінку, звідки користувача перенаправили на вхід
            nxt = request.POST.get("next") or request.GET.get("next") or ""
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(home_redirect(user))
    return render(request, "hotel/login.html", {"next": request.GET.get("next", "")})


def logout_view(request):
    logout(request)
    return redirect("login")


def toggle_lang(request):
    request.session["lang"] = "uk" if _lang(request) == "en" else "en"
    return redirect(request.META.get("HTTP_REFERER") or home_redirect(request.user))


def toggle_theme(request):
    request.session["theme"] = "dark" if request.session.get("theme", "light") == "light" else "light"
    return redirect(request.META.get("HTTP_REFERER") or home_redirect(request.user))


# ---------- публічний сайт (Фаза 1: головна, каталог, пошук) ----------

# Тексти статичних сторінок футера (ключ = англ. текст, UK — у l10n)
STATIC_PAGES = {
    "terms": {
        "title": "Terms of Service",
        "body": "By making a reservation at GrandStay you agree to arrive on the selected date, "
                "keep the room in good condition and follow the hotel rules. Cancellation is free "
                "24 hours before check-in; later cancellations may be charged one night.",
    },
    "privacy": {
        "title": "Privacy Policy",
        "body": "GrandStay stores only the data you provide for a booking: name, e-mail, phone and "
                "stay dates. We never sell or share your data with third parties and you can ask us "
                "to delete your account at any time.",
    },
    "help": {
        "title": "Help Center",
        "body": "Need help? E-mail support@grandstay.example or call +380 44 000 00 00 (24/7). "
                "You can manage your bookings in the My Bookings section after signing in.",
    },
}


def _get_search(request):
    g = request.GET
    return (
        g.get("location", "").strip(),
        g.get("check_in", "").strip(),
        g.get("check_out", "").strip(),
        g.get("guests", "").strip(),
    )


def _parse_search(location, check_in, check_out, guests):
    """(location, date|None, date|None, int|None, error_key|None)."""
    d_in = d_out = None
    for raw, target in ((check_in, "in"), (check_out, "out")):
        if not raw:
            continue
        try:
            parsed = date.fromisoformat(raw)
        except ValueError:
            return location, None, None, None, "Invalid date format"
        if target == "in":
            d_in = parsed
        else:
            d_out = parsed
    if d_in and d_out and d_out <= d_in:
        return location, None, None, None, "Check out must be later"
    n_guests = None
    if guests:
        try:
            # не більше за глобальний максимум (Suite → 8 гостей)
            n_guests = min(max(int(guests), 1), MAX_GUESTS)
        except ValueError:
            return location, None, None, None, "Invalid guests count"
    return location, d_in, d_out, n_guests, None


def _annotate_cards(rooms, d_in, d_out):
    """Позначає кожну картку: вільна/зайнята + ключ бейджа для перекладу."""
    for r in rooms:
        free = room_is_free(r, d_in, d_out)
        r.free = free
        r.badge_kind = "ok" if free else "busy"
        if d_in and d_out:
            r.badge_key = "Free for your dates" if free else "Booked"
        else:
            r.badge_key = "Available now" if free else "Booked"
    return rooms


def _search_context(location, d_in, d_out, guests, raw):
    return {
        "location": location,
        "check_in": d_in.isoformat() if d_in else "",
        "check_out": d_out.isoformat() if d_out else "",
        "guests": str(guests) if guests else "",
        "raw": raw,
        "d_in": d_in,
        "d_out": d_out,
        # ліміт поля Guests на публічних формах (MAX_GUESTS = 8)
        "max_guests": MAX_GUESTS,
    }


def home_view(request):
    """Публічна головна: hero + пошук + рекомендовані місця + CTA."""
    location, ci_raw, co_raw, guests_raw = _get_search(request)
    location, d_in, d_out, guests, error = _parse_search(location, ci_raw, co_raw, guests_raw)
    if error:
        messages.error(request, error)
    rooms = list(search_rooms(location, d_in, d_out, guests).prefetch_related("services")[:6])
    _annotate_cards(rooms, d_in, d_out)
    return render(request, "hotel/home.html", {
        "rooms": rooms,
        "found": search_rooms(location, d_in, d_out, guests).count(),
        "search": _search_context(location, d_in, d_out, guests,
                                  {"location": location, "check_in": ci_raw,
                                   "check_out": co_raw, "guests": guests_raw}),
        "pages": STATIC_PAGES,
    })


def places_view(request):
    """Каталог/результати пошуку з перевіркою вільності дат."""
    location, ci_raw, co_raw, guests_raw = _get_search(request)
    location, d_in, d_out, guests, error = _parse_search(location, ci_raw, co_raw, guests_raw)
    if error:
        messages.error(request, error)
    rooms = list(search_rooms(location, d_in, d_out, guests).prefetch_related("services"))
    _annotate_cards(rooms, d_in, d_out)
    return render(request, "hotel/places.html", {
        "rooms": rooms,
        "found": len(rooms),
        "search": _search_context(location, d_in, d_out, guests,
                                  {"location": location, "check_in": ci_raw,
                                   "check_out": co_raw, "guests": guests_raw}),
        "has_filters": bool(location or d_in or d_out or guests),
        "pages": STATIC_PAGES,
    })


def place_detail_view(request, number):
    """
    Фаза 2: сторінка місця — фото, деталі, чек і кнопка «Забронювати · $134».

    Дати/гостей приносять із пошуку (?check_in=&check_out=&guests=) або міняють
    прямо тут (GET-форма). Чек: ціна × ночі + сервісний збір 12%.
    Кнопка веде на форму бронювання з префілом; недоступна, якщо номер зайнятий
    на обрані дати або не вміщує стільки гостей.
    """
    room = get_object_or_404(Room, number=number)
    location, ci_raw, co_raw, guests_raw = _get_search(request)
    _, d_in, d_out, guests, error = _parse_search(location, ci_raw, co_raw, guests_raw)
    if error:
        messages.error(request, error)

    _annotate_cards([room], d_in, d_out)  # room.free + бейдж
    nights = (d_out - d_in).days if d_in and d_out else 0
    subtotal = room.price * nights if nights else Decimal("0")
    fee = calc_service_fee(subtotal)
    total = subtotal + fee
    fits = not guests or guests <= room.capacity
    can_book = room.free and fits

    # Схожі номери: спершу те саме місто, якщо порожньо — будь-які інші
    city = room.location.split(",")[0].strip()
    others = list(
        search_rooms(city, d_in, d_out, guests).exclude(pk=room.pk)
        .prefetch_related("services")[:3]
    )
    if not others:
        others = list(
            search_rooms("", d_in, d_out, guests).exclude(pk=room.pk)
            .prefetch_related("services")[:3]
        )
    _annotate_cards(others, d_in, d_out)

    return render(request, "hotel/place.html", {
        "room": room,
        "nights": nights,
        "subtotal": subtotal,
        "fee": fee,
        "total": total,
        "fits": fits,
        "can_book": can_book,
        "others": others,
        "search": _search_context(location, d_in, d_out, guests,
                                  {"location": location, "check_in": ci_raw,
                                   "check_out": co_raw, "guests": guests_raw}),
        "pages": STATIC_PAGES,
    })


def page_view(request, slug):
    """Статичні сторінки футера: Terms / Privacy / Help."""
    from django.http import Http404
    page = STATIC_PAGES.get(slug)
    if page is None:
        raise Http404
    return render(request, "hotel/page.html", {"page": page, "slug": slug, "pages": STATIC_PAGES})


# ---------- dashboard (port of views/dashboard.py) ----------

@admin_required
def dashboard_view(request):
    total_rev = calc_total_revenue()
    res_rev = calc_reservation_revenue()
    svc_rev = calc_service_revenue()
    occupancy = get_occupancy_rate()
    rooms = list(Room.objects.all())
    avail = sum(1 for r in rooms if r.status == "Available")
    counts = arrivals_count()
    checked_in = counts["checked_in"]
    recent = list(Reservation.objects.select_related("guest", "room").all()[:6])
    svc_summary = get_services_summary()
    max_rev = max([float(s["revenue"]) for s in svc_summary], default=1) or 1
    for s in svc_summary:
        s["pct"] = round(float(s["revenue"]) / max_rev * 100)
    return render(request, "hotel/dashboard.html", {
        "total_rev": total_rev, "res_rev": res_rev, "svc_rev": svc_rev,
        "occupancy": occupancy, "rooms": rooms, "avail": avail,
        "occupied": len(rooms) - avail,
        "arrivals": counts["active"], "arrivals_today": counts["today"],
        "checked_in": checked_in, "recent": recent,
        "svc_summary": svc_summary,
    })


# ---------- rooms (port of views/rooms.py) ----------

@admin_required
def rooms_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            number = request.POST.get("number", "").strip()
            room_type = request.POST.get("room_type", "Single")
            title = request.POST.get("title", "").strip()
            location = request.POST.get("location", "").strip()
            try:
                price = float(request.POST.get("price", "0") or 0)
            except ValueError:
                messages.error(request, "Invalid price")
                return redirect("rooms")
            # Перевірка місткості за типом: Single → 1, Double → 2, Suite → до 8
            raw_capacity = request.POST.get("capacity", "").strip()
            if raw_capacity:
                try:
                    capacity = int(raw_capacity)
                except ValueError:
                    messages.error(request, "Invalid capacity")
                    return redirect("rooms")
            else:
                # порожнє поле → значення, що точно влізає в ліміт типу
                capacity = min(2, ROOM_CAPACITY_LIMITS.get(room_type, 2))
            capacity_err = capacity_error(room_type, capacity)
            if capacity_err:
                messages.error(request, capacity_err)
                return redirect("rooms")
            photo = request.FILES.get("photo")
            # Галочки «що є в цьому номері» — id з каталогу послуг (hotel_service)
            service_ids = [s for s in request.POST.getlist("services") if s.isdigit()]
            if not number:
                messages.error(request, "Enter a room number")
            elif Room.objects.filter(number=number).exists():
                messages.error(request, f"Room {number} already exists")
            else:
                room = Room.objects.create(
                    number=number, room_type=room_type, price=price,
                    title=title, location=location, capacity=capacity,
                    photo=photo,
                )
                if service_ids:
                    room.services.set(Service.objects.filter(pk__in=service_ids))
                messages.success(request, f"Room {number} added")
            return redirect("rooms")
        if action == "delete":
            number = request.POST.get("number", "").strip()
            if not number:
                messages.error(request, "Enter a room number")
                return redirect("rooms")
            room = Room.objects.filter(number=number).first()
            if not room:
                messages.error(request, f"Room {number} not found")
            elif Reservation.objects.filter(room=room).exists() or room.status != "Available":
                messages.error(request, f"Cannot delete room {number} — it has active reservations")
            else:
                room.delete()
                messages.success(request, f"Room {number} deleted")
            return redirect("rooms")
        if action == "status":
            room = get_object_or_404(Room, pk=request.POST.get("room_id"))
            room.status = request.POST.get("status", room.status)
            room.save()
            return redirect("rooms")
    return render(request, "hotel/rooms.html", {
        "rooms": Room.objects.prefetch_related("services").all(),
        "catalog": Service.objects.all(),
        "max_guests": MAX_GUESTS,
    })


# ---------- reservations (port of views/reservations.py) ----------

COUNTRY_CODES = ["+380", "+1", "+44", "+49", "+33", "+48", "+39", "+34", "+90", "+81", "+86", "+91"]

@login_required
def reservations_view(request):
    admin = is_admin(request.user)
    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "status":
            # Змінювати статуси (заселення/виселення) може лише адміністратор
            if not admin:
                messages.error(request, "Access restricted to administrators")
                return redirect("reservations")
            res = get_object_or_404(Reservation, pk=request.POST.get("reservation_id"))
            new_status = request.POST.get("status", res.status)
            # Виселення можливе лише після оплати додаткових послуг,
            # як у реальному готелі: рахунок закривають перед виїздом.
            if new_status == "Checked-Out" and res.extras_due > 0:
                messages.error(request, "Pay the extras before checkout")
                return redirect("reservation_detail", pk=res.pk)
            res.status = new_status
            res.save()
            # keep room status in sync (port of create_reservation side-effect)
            if new_status == "Checked-In":
                res.room.status = "Occupied"
                res.room.save()
            elif new_status == "Checked-Out":
                res.room.status = "Available"
                res.room.save()
            messages.success(request, f"Reservation {res.pk} updated")
            return redirect("reservations")
        # create
        name = request.POST.get("guest_name", "").strip()
        code = request.POST.get("country_code", "+380")
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        room_number = request.POST.get("room_number", "")
        check_in = request.POST.get("check_in", "")
        check_out = request.POST.get("check_out", "")
        if not name:
            messages.error(request, "Enter guest name")
        elif not email or not _validate_email(email):
            messages.error(request, "Invalid email")
        elif not room_number:
            messages.error(request, "Select room")
        elif not check_in:
            messages.error(request, "Select check in date")
        elif not check_out:
            messages.error(request, "Select check out date")
        elif check_out <= check_in:
            messages.error(request, "Check out must be later")
        else:
            room = Room.objects.filter(number=room_number, status="Available").first()
            if not room:
                messages.error(request, "Reservation failed")
            else:
                guest = Guest.objects.create(name=name, phone=f"{code}{phone}", email=email)
                res = Reservation(
                    guest=guest, room=room, check_in=check_in, check_out=check_out,
                    user=request.user,
                )
                try:
                    res.full_clean()
                    res.save()
                    room.status = "Occupied"
                    room.save()
                    messages.success(request, "Reservation created")
                except ValidationError as e:
                    guest.delete()
                    messages.error(request, "Reservation failed")
            return redirect("reservations")
    reservations = Reservation.objects.select_related("guest", "room").all()
    if not admin:
        # Звичайний користувач бачить лише власні бронювання
        reservations = reservations.filter(user=request.user)
    # Префіл із публічного каталогу: /reservations/?room=101&check_in=...&check_out=...
    prefill_room = request.GET.get("room", "").strip()
    prefill_in = request.GET.get("check_in", "").strip()
    prefill_out = request.GET.get("check_out", "").strip()
    available_rooms = Room.objects.filter(status="Available")
    if prefill_room:
        available_rooms = Room.objects.filter(Q(status="Available") | Q(number=prefill_room))
    return render(request, "hotel/reservations.html", {
        "reservations": reservations,
        "available_rooms": available_rooms,
        "country_codes": COUNTRY_CODES,
        "today": date.today().isoformat(),
        "can_manage": admin,
        "prefill_email": "" if admin else request.user.email,
        "prefill_room": prefill_room,
        "prefill_check_in": prefill_in,
        "prefill_check_out": prefill_out,
    })


# ---------- guests (port of views/guests.py) ----------

@admin_required
def guests_view(request):
    q = request.GET.get("q", "").strip()
    guests = Guest.objects.all()
    if q:
        guests = guests.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    return render(request, "hotel/guests.html", {"guests": guests, "q": q})


# ---------- деталі бронювання + додаткові послуги ----------

@login_required
def reservation_detail_view(request, pk):
    """
    Сторінка бронювання: склад проживання + додаткові послуги.

    Послуги замовляють тут (з каталогу), а оплачують перед виселенням —
    кнопка «Pay before checkout». Доступ: власник бронювання або адміністратор.
    (Сторінка /services/ прибрана — послуги живуть у базі даних.)
    """
    res = get_object_or_404(
        Reservation.objects.select_related("guest", "room"), pk=pk
    )
    owner = is_admin(request.user) or res.user_id == request.user.id
    if not owner:
        messages.error(request, "This booking is not available to you")
        return redirect("profile")

    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "add":
            if res.status == "Checked-Out":
                messages.error(request, "The stay is already over")
                return redirect("reservation_detail", pk=res.pk)
            selected = [s for s in request.POST.getlist("service") if s.isdigit()]
            if not selected:
                messages.error(request, "Select at least one service")
                return redirect("reservation_detail", pk=res.pk)
            created = 0
            for service_id in selected:
                svc = Service.objects.filter(pk=service_id).first()
                if svc is None:
                    continue
                try:
                    qty = int(request.POST.get(f"qty_{service_id}", "1") or 1)
                    if qty < 1:
                        raise ValueError
                except ValueError:
                    messages.error(request, f"Invalid quantity for {svc.name}")
                    return redirect("reservation_detail", pk=res.pk)
                ServiceOrder.objects.create(
                    guest=res.guest, reservation=res,
                    service_name=svc.name, service_price=svc.price,
                    quantity=qty,
                )
                created += 1
            if created:
                messages.success(request, "Services ordered")
            else:
                messages.error(request, "Failed to create orders")
            return redirect("reservation_detail", pk=res.pk)

        if action == "pay":
            paid = res.service_orders.filter(paid=False).exclude(status="Cancelled")
            count = paid.update(paid=True)
            if count:
                messages.success(request, "Payment successful")
            else:
                messages.error(request, "Nothing to pay")
            return redirect("reservation_detail", pk=res.pk)

    orders = list(res.service_orders.all())
    context = {
        "res": res,
        "orders": orders,
        "catalog": Service.objects.all(),
        "extras_total": res.extras_total,
        "extras_due": res.extras_due,
        "grand_total": res.total + res.extras_total,
        "can_order": res.status != "Checked-Out",
        "can_manage": is_admin(request.user),
        "pages": STATIC_PAGES,
    }
    return render(request, "hotel/reservation.html", context)


# ---------- profile (new page for the user's own info) ----------

@login_required
def profile_view(request):
    user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "email":
            email = request.POST.get("email", "").strip()
            if not email:
                messages.error(request, "Invalid email")
            else:
                user.email = email
                user.save()
                messages.success(request, "Profile updated")
            return redirect("profile")
        if action == "password":
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed")
            else:
                for err in form.errors.values():
                    messages.error(request, " ".join(err))
            return redirect("profile")

    admin = is_admin(user)
    if admin:
        # Адміністратор: загальна статистика готелю + всі бронювання
        stats = {
            "guests": Guest.objects.count(),
            "reservations": Reservation.objects.count(),
            "orders": ServiceOrder.objects.count(),
            "rooms": Room.objects.count(),
            "revenue": calc_total_revenue(),
            "occupancy": get_occupancy_rate(),
            "checked_in": arrivals_count()["checked_in"],
        }
        recent = list(Reservation.objects.select_related("guest", "room").all()[:5])
    else:
        # Звичайний користувач: лише його власні дані
        mine = list(Reservation.objects.filter(user=user).select_related("guest", "room"))
        my_guests = Guest.objects.filter(reservations__user=user).distinct()
        stats = {
            "my_reservations": len(mine),
            "nights": sum(r.nights for r in mine),
            "amount": sum((r.amount for r in mine), start=Decimal("0")),
            "orders": ServiceOrder.objects.filter(guest__in=my_guests).count(),
            "checked_in": sum(1 for r in mine if r.status == "Checked-In"),
        }
        recent = mine[:5]
    return render(request, "hotel/profile.html", {
        "stats": stats,
        "recent": recent,
        "is_admin": admin,
        "pw_form": PasswordChangeForm(user),
    })
