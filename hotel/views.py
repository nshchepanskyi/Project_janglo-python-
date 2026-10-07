import re
from datetime import date

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
    SERVICES_CATALOG,
    Guest,
    Reservation,
    Room,
    ServiceOrder,
    arrivals_count,
    calc_reservation_revenue,
    calc_service_revenue,
    calc_total_revenue,
    get_occupancy_rate,
    get_services_summary,
)


def _lang(request):
    return request.session.get("lang", "en")


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
        return redirect("dashboard")
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
        return redirect("dashboard")
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
            return redirect("dashboard")
    return render(request, "hotel/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def toggle_lang(request):
    request.session["lang"] = "uk" if _lang(request) == "en" else "en"
    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


def toggle_theme(request):
    request.session["theme"] = "dark" if request.session.get("theme", "light") == "light" else "light"
    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


# ---------- dashboard (port of views/dashboard.py) ----------

@login_required
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

@login_required
def rooms_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            number = request.POST.get("number", "").strip()
            room_type = request.POST.get("room_type", "Single")
            try:
                price = float(request.POST.get("price", "0") or 0)
            except ValueError:
                messages.error(request, "Invalid price")
                return redirect("rooms")
            if not number:
                messages.error(request, "Enter a room number")
            elif Room.objects.filter(number=number).exists():
                messages.error(request, f"Room {number} already exists")
            else:
                Room.objects.create(number=number, room_type=room_type, price=price)
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
    return render(request, "hotel/rooms.html", {"rooms": Room.objects.all()})


# ---------- reservations (port of views/reservations.py) ----------

COUNTRY_CODES = ["+380", "+1", "+44", "+49", "+33", "+48", "+39", "+34", "+90", "+81", "+86", "+91"]

@login_required
def reservations_view(request):
    if request.method == "POST":
        action = request.POST.get("action", "create")
        if action == "status":
            res = get_object_or_404(Reservation, pk=request.POST.get("reservation_id"))
            new_status = request.POST.get("status", res.status)
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
                res = Reservation(guest=guest, room=room, check_in=check_in, check_out=check_out)
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
    available_rooms = Room.objects.filter(status="Available")
    return render(request, "hotel/reservations.html", {
        "reservations": reservations,
        "available_rooms": available_rooms,
        "country_codes": COUNTRY_CODES,
        "today": date.today().isoformat(),
    })


# ---------- guests (port of views/guests.py) ----------

@login_required
def guests_view(request):
    q = request.GET.get("q", "").strip()
    guests = Guest.objects.all()
    if q:
        guests = guests.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    return render(request, "hotel/guests.html", {"guests": guests, "q": q})


# ---------- services (port of views/services.py) ----------

@login_required
def services_view(request):
    if request.method == "POST":
        action = request.POST.get("action", "order")
        if action == "status":
            order = get_object_or_404(ServiceOrder, pk=request.POST.get("order_id"))
            order.status = request.POST.get("status", order.status)
            order.save()
            messages.success(request, f"Order {order.pk} updated")
            return redirect("services")
        guest_id = request.POST.get("guest_id", "")
        selected = request.POST.getlist("service")
        if not selected:
            messages.error(request, "Select at least one service")
            return redirect("services")
        guest = Guest.objects.filter(pk=guest_id).first()
        if not guest:
            messages.error(request, "Select guest")
            return redirect("services")
        created = 0
        for name in selected:
            try:
                qty = int(request.POST.get(f"qty_{name}", "1") or 1)
                if qty < 1:
                    raise ValueError
            except ValueError:
                messages.error(request, f"Invalid quantity for {name}")
                return redirect("services")
            price = next((s["price"] for s in SERVICES_CATALOG if s["name"] == name), None)
            if price is None:
                continue
            ServiceOrder.objects.create(guest=guest, service_name=name, service_price=price, quantity=qty)
            created += 1
        if created:
            messages.success(request, f"{created} order(s) created")
        else:
            messages.error(request, "Failed to create orders")
        return redirect("services")
    orders = ServiceOrder.objects.select_related("guest").all()
    return render(request, "hotel/services.html", {
        "catalog": SERVICES_CATALOG,
        "guests": Guest.objects.all(),
        "orders": orders,
    })


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
    return render(request, "hotel/profile.html", {
        "stats": stats,
        "recent": recent,
        "pw_form": PasswordChangeForm(user),
    })
