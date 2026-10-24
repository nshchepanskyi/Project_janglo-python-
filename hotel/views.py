import re
import secrets
import string
import time
from datetime import date
from decimal import Decimal
from functools import wraps
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.mail.message import BadHeaderError
from django.core.validators import validate_email as django_validate_email
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from config import email_service

from .models import (
    ACTIVE_STATUSES,
    Guest,
    MAX_GUESTS,
    Profile,
    ROOM_CAPACITY_LIMITS,
    Reservation,
    Review,
    Room,
    RoomFavorite,
    Service,
    ServiceOrder,
    STAY_DAY,
    STAY_NIGHT,
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
from .forms import ShareRoomForm


MAX_AVATAR_BYTES = 2 * 1024 * 1024
REGISTRATION_CODE_LENGTH = 6
REGISTRATION_CODE_TTL_SECONDS = 10 * 60
REGISTRATION_CODE_MAX_ATTEMPTS = 10
REGISTRATION_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _lang(request):
    return request.session.get("lang", "en")


def _msg(request, key, **kwargs):
    """Перекладає повідомлення з плейсхолдерами за мовою сесії.

    Шаблони показують повідомлення через {% tr m %}, але ключ на кшталт
    «Room {number} added» не збігається з уже відформатованим рядком —
    тому такі повідомлення перекладаємо тут, одразу з параметрами.
    """
    from . import l10n
    prev = l10n.CURRENT_LANG
    l10n.CURRENT_LANG = request.session.get("lang", "en")
    try:
        return l10n.tr(key, **kwargs)
    finally:
        l10n.CURRENT_LANG = prev




def is_admin(user):
    """Адміністратор = персонал/суперкористувач (керує всім функціоналом)."""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def home_redirect(user):
    """Куди відправляти після входу/реєстрації."""
    return "hotel:dashboard" if is_admin(user) else "hotel:profile"


def admin_required(view_func):
    """Лише для адміністратора; звичайний користувач потрапляє у профіль."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Access restricted to administrators")
            return redirect("hotel:profile")
        return view_func(request, *args, **kwargs)
    return login_required(wrapper)




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


def _new_registration_code():
    return "".join(
        secrets.choice(REGISTRATION_CODE_ALPHABET)
        for _ in range(REGISTRATION_CODE_LENGTH)
    )


def _verification_uses_resend():
    """Вирішує, як надсилати лист.

    Render Free блокує SMTP-порти (25/465/587), тому у продакшені код
    підтвердження йде через HTTPS API Resend. Локально (console) і в тестах
    (locmem) листи залишаються у штатному Django-бекенді.
    """
    return (
        email_service.is_configured()
        and settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
    )


def _send_registration_code(user, code):
    body = (
        f"Hello {user.username},\n\n"
        "Welcome to GrandStay!\n"
        f"Your email verification code is: {code}\n\n"
        "Enter this 6-character code on the verification page to confirm "
        "that this email address belongs to you. The code expires in 10 minutes.\n\n"
        "If you did not create a GrandStay account, you can ignore this email.\n\n"
        "GrandStay team"
    )
    if _verification_uses_resend():
        html = (
            "<p>Hello "
            + user.username
            + ",</p><p>Welcome to <strong>GrandStay</strong>!</p>"
            "<p>Your email verification code is: "
            f"<strong style='font-size:20px;letter-spacing:3px'>{code}</strong></p>"
            "<p>Enter this 6-character code on the verification page to confirm "
            "that this email address belongs to you. The code expires in "
            "10 minutes.</p>"
            "<p>If you did not create a GrandStay account, you can ignore "
            "this email.</p><p>GrandStay team</p>"
        )
        return 1 if email_service.send_email_safe(
            user.email, "Verify your email address — GrandStay", html, text=body
        ) else 0
    try:
        return send_mail(
            subject="Verify your email address — GrandStay",
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except (BadHeaderError, OSError, SMTPException):
        return 0


def _verification_delivery_message():
    if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        return "Development email printed to server console."
    return "Verification code sent. Check your email."


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
        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists")
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists")
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password, is_active=False,
            )
            code = _new_registration_code()
            if not _send_registration_code(user, code):
                user.delete()
                messages.error(request, "Verification email could not be sent. Please try again.")
            else:
                request.session["pending_registration"] = {
                    "user_id": user.pk,
                    "code_hash": make_password(code),
                    "expires_at": int(time.time()) + REGISTRATION_CODE_TTL_SECONDS,
                    "attempts": 0,
                }
                messages.success(request, _verification_delivery_message())
                return redirect("hotel:verify_email")
    return render(request, "hotel/register.html")


def verify_email_view(request):
    pending = request.session.get("pending_registration")
    if request.user.is_authenticated and not isinstance(pending, dict):
        return redirect(home_redirect(request.user))
    if not isinstance(pending, dict):
        messages.error(request, "Verification session expired. Please register again.")
        return redirect("hotel:register")

    user = User.objects.filter(pk=pending.get("user_id"), is_active=False).first()
    if user is None:
        request.session.pop("pending_registration", None)
        messages.error(request, "Verification session expired. Please register again.")
        return redirect("hotel:register")

    if request.method == "POST":
        if request.POST.get("action") == "resend":
            code = _new_registration_code()
            if _send_registration_code(user, code):
                pending.update({
                    "code_hash": make_password(code),
                    "expires_at": int(time.time()) + REGISTRATION_CODE_TTL_SECONDS,
                    "attempts": 0,
                })
                request.session["pending_registration"] = pending
                messages.success(request, _verification_delivery_message())
            else:
                messages.error(request, "Verification email could not be sent. Please try again.")
            return redirect("hotel:verify_email")

        if int(time.time()) >= int(pending.get("expires_at", 0)):
            messages.error(request, "Verification code expired. Please request a new one.")
        elif int(pending.get("attempts", 0)) >= REGISTRATION_CODE_MAX_ATTEMPTS:
            messages.error(request, "Too many incorrect attempts. Please request a new code.")
        else:
            code = request.POST.get("code", "").strip().upper()
            code_hash = pending.get("code_hash", "")
            if re.fullmatch(r"[A-Z0-9]{6}", code) and check_password(code, code_hash):
                user.is_active = True
                user.save(update_fields=["is_active"])
                request.session.pop("pending_registration", None)
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, "Email verified. Welcome to GrandStay!")
                return redirect("hotel:home")

            pending["attempts"] = int(pending.get("attempts", 0)) + 1
            request.session["pending_registration"] = pending
            messages.error(request, "Invalid verification code")

    return render(request, "hotel/verify_email.html", {"email": user.email})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(home_redirect(request.user))
    if request.method == "POST":
        login_input = request.POST.get("login", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=login_input, password=password)
        if user is None:

            try:
                u = User.objects.get(email=login_input)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is None:
            messages.error(request, "Invalid credentials")
        else:
            login(request, user)

            nxt = request.POST.get("next") or request.GET.get("next") or ""
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(home_redirect(user))
    return render(request, "hotel/login.html", {"next": request.GET.get("next", "")})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("hotel:login")


def toggle_lang(request):
    request.session["lang"] = "uk" if _lang(request) == "en" else "en"
    return redirect(request.META.get("HTTP_REFERER") or home_redirect(request.user))


def toggle_theme(request):
    request.session["theme"] = "dark" if request.session.get("theme", "light") == "light" else "light"
    return redirect(request.META.get("HTTP_REFERER") or home_redirect(request.user))





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


def _fav_annotate(request, rooms):
    """Додає до карток ознаку «в обраному» (★) для залогіненого гостя."""
    if request.user.is_authenticated:
        fav_ids = set(request.user.favorite_rooms.values_list("room_id", flat=True))
        for r in rooms:
            r.fav = r.pk in fav_ids
    else:
        for r in rooms:
            r.fav = False
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

        "max_guests": MAX_GUESTS,
    }


def home_view(request):
    """Публічна головна: hero + пошук + рекомендовані місця + CTA."""
    location, ci_raw, co_raw, guests_raw = _get_search(request)
    location, d_in, d_out, guests, error = _parse_search(location, ci_raw, co_raw, guests_raw)
    if error:
        messages.error(request, error)
    rooms = list(search_rooms(location, d_in, d_out, guests).prefetch_related("services"))
    _annotate_cards(rooms, d_in, d_out)
    _fav_annotate(request, rooms)
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
    _fav_annotate(request, rooms)
    return render(request, "hotel/places.html", {
        "rooms": rooms,
        "found": len(rooms),
        "search": _search_context(location, d_in, d_out, guests,
                                  {"location": location, "check_in": ci_raw,
                                   "check_out": co_raw, "guests": guests_raw}),
        "has_filters": bool(location or d_in or d_out or guests),
        "pages": STATIC_PAGES,
    })


def _create_review(request, room):
    """Відгук: лише після виселення з цього номера, одне повідомлення на бронювання.

    Чесна схема «гість реально жив у цьому номері»: бронювання має належати
    автору, бути в статусі Checked-Out і ще не мати відгуку (Review.reservation
    — OneToOneField). Після створення сигнал оновить Room.rating.
    """
    res = Reservation.objects.filter(
        pk=request.POST.get("reservation_id"),
        user=request.user, room=room, status="Checked-Out",
    ).first()
    if res is None:
        messages.error(request, "Only a checked-out guest can leave a review")
        return redirect("hotel:place_detail", number=room.number)
    if Review.objects.filter(reservation=res).exists():
        messages.error(request, "You have already reviewed this stay")
        return redirect("hotel:place_detail", number=room.number)
    try:
        rating = int(request.POST.get("rating", "0"))
    except ValueError:
        rating = 0
    text = request.POST.get("text", "").strip()
    if not (Review.RATING_MIN <= rating <= Review.RATING_MAX):
        messages.error(request, "Rating must be between 1 and 5")
    elif not text:
        messages.error(request, "Write a few words about your stay")
    else:
        Review.objects.create(reservation=res, room=room, author=request.user,
                              rating=rating, text=text)
        messages.success(request, "Thank you for your review!")
    return redirect("hotel:place_detail", number=room.number)


def place_detail_view(request, number):
    """
    Фаза 2: сторінка місця — фото, деталі, чек і кнопка «Забронювати · $134».

    Дати/гостей приносять із пошуку (?check_in=&check_out=&guests=) або міняють
    прямо тут (GET-форма). Чек: ціна × ночі + сервісний збір 12%.
    Кнопка веде на форму бронювання з префілом; недоступна, якщо номер зайнятий
    на обрані дати або не вміщує стільки гостей.

    Фаза 3: зірочка обраного + відгуки (лише після виселення) з живим рейтингом.
    """
    room = get_object_or_404(Room, number=number)
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('hotel:login')}?next={reverse('hotel:place_detail', args=[number])}")
        return _create_review(request, room)
    location, ci_raw, co_raw, guests_raw = _get_search(request)
    _, d_in, d_out, guests, error = _parse_search(location, ci_raw, co_raw, guests_raw)
    if error:
        messages.error(request, error)

    _annotate_cards([room], d_in, d_out)
    _fav_annotate(request, [room])
    nights = (d_out - d_in).days if d_in and d_out else 0
    subtotal = room.price * nights if nights else Decimal("0")
    fee = calc_service_fee(subtotal)
    total = subtotal + fee
    fits = not guests or guests <= room.capacity
    can_book = room.free and fits


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
    _fav_annotate(request, others)



    reviews = list(room.reviews.select_related("author")[:30])
    reviewable = []
    if request.user.is_authenticated:
        reviewable = list(
            Reservation.objects.filter(
                user=request.user, room=room, status="Checked-Out",
            ).exclude(review__isnull=False)
        )

    return render(request, "hotel/place.html", {
        "room": room,
        "nights": nights,
        "subtotal": subtotal,
        "fee": fee,
        "total": total,
        "fits": fits,
        "can_book": can_book,
        "others": others,
        "reviews": reviews,
        "reviewable": reviewable,
        "can_review": bool(reviewable),
        "review_res": reviewable[0] if reviewable else None,
        "search": _search_context(location, d_in, d_out, guests,
                                  {"location": location, "check_in": ci_raw,
                                   "check_out": co_raw, "guests": guests_raw}),
        "pages": STATIC_PAGES,
    })


def share_room_view(request, number):
    """Send a room recommendation with a link to its public detail page."""
    room = get_object_or_404(Room, number=number)
    if request.method == "POST":
        form = ShareRoomForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            public_url = reverse("hotel:place_detail", kwargs={"number": room.number})
            share_url = request.build_absolute_uri(public_url)
            message = render_to_string("hotel/email/share_room.txt", {
                "room": room,
                "name": data["name"],
                "email": data["email"],
                "comments": data["comments"],
                "share_url": share_url,
            })
            try:
                sent = send_mail(
                    subject=f"{data['name']} recommends a room at GrandStay",
                    message=message,
                    from_email=None,
                    recipient_list=[data["to"]],
                    fail_silently=False,
                )
            except (BadHeaderError, OSError, SMTPException):
                sent = 0

            if sent:
                messages.success(request, "Recommendation email sent")
                return redirect(public_url)
            messages.error(request, "Email could not be sent. Check the email settings and try again.")
    else:
        form = ShareRoomForm()

    return render(request, "hotel/share_room.html", {"room": room, "form": form})


@login_required
def favorites_view(request):
    """Фаза 3: сторінка «Обране» — картки збережених номерів."""
    rooms = list(Room.objects.filter(favorited_by__user=request.user)
                 .prefetch_related("services"))
    _annotate_cards(rooms, None, None)
    _fav_annotate(request, rooms)
    return render(request, "hotel/favorites.html", {
        "rooms": rooms,
        "search": _search_context("", None, None, None,
                                  {"location": "", "check_in": "",
                                   "check_out": "", "guests": ""}),
        "pages": STATIC_PAGES,
    })


def favorite_toggle_view(request, number):
    """Зірочка «в обране»: POST-перемикач. Анонім → вхід з ?next=."""
    room = get_object_or_404(Room, number=number)
    if not request.user.is_authenticated:
        return redirect(
            f"{reverse('hotel:login')}?next={reverse('hotel:favorite_toggle', args=[number])}"
        )
    if request.method == "POST":
        fav = RoomFavorite.objects.filter(user=request.user, room=room).first()
        if fav:
            fav.delete()
            messages.success(request, "Removed from favorites")
        else:
            RoomFavorite.objects.create(user=request.user, room=room)
            messages.success(request, "Added to favorites")

    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("hotel:place_detail", number=number)


def page_view(request, slug):
    """Статичні сторінки футера: Terms / Privacy / Help."""
    from django.http import Http404
    page = STATIC_PAGES.get(slug)
    if page is None:
        raise Http404
    return render(request, "hotel/page.html", {"page": page, "slug": slug, "pages": STATIC_PAGES})




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
                return redirect("hotel:rooms")

            raw_capacity = request.POST.get("capacity", "").strip()
            if raw_capacity:
                try:
                    capacity = int(raw_capacity)
                except ValueError:
                    messages.error(request, "Invalid capacity")
                    return redirect("hotel:rooms")
            else:

                capacity = min(2, ROOM_CAPACITY_LIMITS.get(room_type, 2))
            capacity_err = capacity_error(room_type, capacity)
            if capacity_err:
                messages.error(request, capacity_err)
                return redirect("hotel:rooms")
            photo = request.FILES.get("photo")

            service_ids = [s for s in request.POST.getlist("services") if s.isdigit()]
            if not number:
                messages.error(request, "Enter a room number")
            elif Room.objects.filter(number=number).exists():
                messages.error(request, _msg(request, "Room {number} already exists", number=number))
            else:
                room = Room.objects.create(
                    number=number, room_type=room_type, price=price,
                    title=title, location=location, capacity=capacity,
                    photo=photo,
                )
                if service_ids:
                    room.services.set(Service.objects.filter(pk__in=service_ids))
                messages.success(request, _msg(request, "Room {number} added", number=number))
            return redirect("hotel:rooms")
        if action == "delete":
            number = request.POST.get("number", "").strip()
            if not number:
                messages.error(request, "Enter a room number")
                return redirect("hotel:rooms")
            room = Room.objects.filter(number=number).first()
            if not room:
                messages.error(request, _msg(request, "Room {number} not found", number=number))
            elif Reservation.objects.filter(room=room).exists() or room.status != "Available":
                messages.error(request, _msg(
                    request, "Cannot delete room {number} — it has active reservations", number=number))
            else:
                room.delete()
                messages.success(request, _msg(request, "Room {number} deleted", number=number))
            return redirect("hotel:rooms")
        if action == "status":
            room = get_object_or_404(Room, pk=request.POST.get("room_id"))
            room.status = request.POST.get("status", room.status)
            room.save()
            return redirect("hotel:rooms")
    return render(request, "hotel/rooms.html", {
        "rooms": Room.objects.prefetch_related("services").all(),
        "catalog": Service.objects.all(),
        "max_guests": MAX_GUESTS,
    })




COUNTRY_CODES = ["+380", "+1", "+44", "+49", "+33", "+48", "+39", "+34", "+90", "+81", "+86", "+91"]


def _validation_message(exc):
    """Зрозуміле повідомлення з ValidationError (в т.ч. з error_dict)."""
    if hasattr(exc, "error_dict"):
        return "; ".join(str(m) for errs in exc.error_dict.values() for err in errs for m in err.messages)
    return "; ".join(str(m) for m in exc.messages)

@login_required
def reservations_view(request):
    admin = is_admin(request.user)
    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "status":

            if not admin:
                messages.error(request, "Access restricted to administrators")
                return redirect("hotel:reservations")
            res = get_object_or_404(Reservation, pk=request.POST.get("reservation_id"))
            new_status = request.POST.get("status", res.status)


            if new_status == "Checked-Out" and res.extras_due > 0:
                messages.error(request, "Pay the extras before checkout")
                return redirect("hotel:reservation_detail", pk=res.pk)
            res.status = new_status
            res.save()

            if new_status == "Checked-In":
                res.room.status = "Occupied"
                res.room.save()
            elif new_status == "Checked-Out":


                still_booked = res.room.reservations.filter(
                    status__in=ACTIVE_STATUSES,
                ).exists()
                res.room.status = "Occupied" if still_booked else "Available"
                res.room.save()
            messages.success(request, _msg(request, "Reservation {pk} updated", pk=res.pk))
            return redirect("hotel:reservations")

        name = request.POST.get("guest_name", "").strip()
        code = request.POST.get("country_code", "+380")
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        room_number = request.POST.get("room_number", "")
        check_in = request.POST.get("check_in", "")
        check_out = request.POST.get("check_out", "")




        stay_type = request.POST.get("stay_type", STAY_NIGHT)
        if stay_type not in (STAY_NIGHT, STAY_DAY):
            stay_type = STAY_NIGHT
        if stay_type == STAY_DAY and check_in:
            check_out = check_in

        try:
            guests = int(request.POST.get("guests", "1") or 1)
        except ValueError:
            guests = 0
        if guests < 1 or guests > MAX_GUESTS:
            messages.error(request, "Invalid guests count")
        elif not name:
            messages.error(request, "Enter guest name")
        elif not email or not _validate_email(email):
            messages.error(request, "Invalid email")
        elif not room_number:
            messages.error(request, "Select room")
        elif not check_in:
            messages.error(request, "Select check in date")
        elif not check_out:
            messages.error(request, "Select check out date")
        elif stay_type != STAY_DAY and check_out <= check_in:
            messages.error(request, "Check out must be later")
        else:



            room = Room.objects.filter(number=room_number) \
                .exclude(status__in=["Cleaning", "Maintenance"]).first()
            if not room:
                messages.error(request, "Reservation failed")
            else:
                guest = Guest.objects.create(name=name, phone=f"{code}{phone}", email=email)
                res = Reservation(
                    guest=guest, room=room, check_in=check_in, check_out=check_out,
                    user=request.user, stay_type=stay_type, guests=guests,
                )
                try:
                    res.full_clean()
                    res.save()
                    room.status = "Occupied"
                    room.save()
                    messages.success(request, "Reservation created")
                except ValidationError as e:
                    guest.delete()
                    messages.error(request, _validation_message(e) or "Reservation failed")
            return redirect("hotel:reservations")
    reservations = Reservation.objects.select_related("guest", "room").all()
    if not admin:

        reservations = reservations.filter(user=request.user)

    prefill_room = request.GET.get("room", "").strip()
    prefill_in = request.GET.get("check_in", "").strip()
    prefill_out = request.GET.get("check_out", "").strip()

    prefill_stay = request.GET.get("stay", "").strip().capitalize()
    if prefill_stay not in ("Night", "Day"):
        prefill_stay = STAY_NIGHT

    try:
        prefill_guests = int(request.GET.get("guests", "1") or 1)
    except ValueError:
        prefill_guests = 1
    prefill_guests = min(max(prefill_guests, 1), MAX_GUESTS)


    bookable = Q(status__in=["Available", "Occupied"])
    available_rooms = Room.objects.filter(bookable)
    if prefill_room:
        available_rooms = Room.objects.filter(bookable | Q(number=prefill_room))
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
        "prefill_stay": prefill_stay,
        "prefill_guests": prefill_guests,
        "guests_choices": list(range(1, MAX_GUESTS + 1)),
    })




@admin_required
def guests_view(request):
    q = request.GET.get("q", "").strip()
    guests = Guest.objects.all()
    if q:
        guests = guests.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    return render(request, "hotel/guests.html", {"guests": guests, "q": q})




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
        return redirect("hotel:profile")

    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "add":
            if res.status == "Checked-Out":
                messages.error(request, "The stay is already over")
                return redirect("hotel:reservation_detail", pk=res.pk)
            selected = [s for s in request.POST.getlist("service") if s.isdigit()]
            if not selected:
                messages.error(request, "Select at least one service")
                return redirect("hotel:reservation_detail", pk=res.pk)
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
                    messages.error(request, _msg(request, "Invalid quantity for {name}", name=svc.name))
                    return redirect("hotel:reservation_detail", pk=res.pk)
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
            return redirect("hotel:reservation_detail", pk=res.pk)

        if action == "pay":
            paid = res.service_orders.filter(paid=False).exclude(status="Cancelled")
            count = paid.update(paid=True)
            if count:
                messages.success(request, "Payment successful")
            else:
                messages.error(request, "Nothing to pay")
            return redirect("hotel:reservation_detail", pk=res.pk)

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




def _update_avatar(request, user):
    """Завантаження/видалення фото профілю (дії з /profile/).

    Перевіряємо розмір (MAX_AVATAR_BYTES), а «це справді зображення»
    гарантує full_clean() ImageField (Pillow). Старий файл прибираємо
    з диска після успішного збереження нового.
    """
    action = request.POST.get("action")
    profile, _ = Profile.objects.get_or_create(user=user)
    if action == "avatar_remove":
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = ""
            profile.save()
            messages.success(request, "Profile photo removed")
        else:
            messages.error(request, "You have no profile photo")
        return redirect("hotel:profile")

    avatar = request.FILES.get("avatar")
    if avatar is None:
        messages.error(request, "Choose a photo")
    elif avatar.size > MAX_AVATAR_BYTES:
        messages.error(request, "Photo must be under 2 MB")
    else:
        prev_name = profile.avatar.name if profile.avatar else ""
        profile.avatar = avatar
        try:
            profile.full_clean()
        except ValidationError as e:
            messages.error(request, _validation_message(e) or "The file must be an image")
        else:
            profile.save()
            if prev_name and prev_name != profile.avatar.name \
                    and default_storage.exists(prev_name):
                default_storage.delete(prev_name)
            messages.success(request, "Profile photo updated")
    return redirect("hotel:profile")


@login_required
def profile_view(request):
    user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        if action in ("avatar", "avatar_remove"):
            return _update_avatar(request, user)
        if action == "email":
            email = request.POST.get("email", "").strip()
            if not email:
                messages.error(request, "Invalid email")
            else:
                user.email = email
                user.save()
                messages.success(request, "Profile updated")
            return redirect("hotel:profile")
        if action == "password":
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed")
            else:
                for err in form.errors.values():
                    messages.error(request, " ".join(err))
            return redirect("hotel:profile")

    admin = is_admin(user)
    if admin:

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
