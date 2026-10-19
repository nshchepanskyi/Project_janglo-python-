"""
Generic Class-Based Views (В6.1–В6.5, В7.3–В7.4).

Повний CRUD бронювань (ReservationListView, ReservationDetailView,
ReservationCreateView, ReservationUpdateView, ReservationDeleteView)
та каталог номерів (RoomListView, RoomDetailView).
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import GuestForm, ReservationForm
from .models import Guest, Reservation, Room, STAY_DAY
from .views import is_admin, STATIC_PAGES


# ---------- допоміжний Mixin: власник або адмін ----------

class OwnerOrAdminMixin:
    """
    Дозволяє редагувати/видаляти запис лише власнику або адміністратору.
    Не адмін і не власник → 403. (В7.3)
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not (is_admin(self.request.user) or getattr(obj, "user_id", None) == self.request.user.id):
            raise PermissionDenied
        return obj


# ============================================================
# Бронювання: повний CRUD на Generic Views
# ============================================================

class ReservationListView(LoginRequiredMixin, ListView):
    """
    Список бронювань: адмін бачить усі, звичайний — лише свої. (В6.1, В6.3)
    Перевизначення get_queryset() (В6.4).
    """
    model = Reservation
    template_name = "hotel/booking_list.html"
    context_object_name = "reservations"
    paginate_by = 10  # В6.3: пагінація

    def get_queryset(self):
        qs = super().get_queryset().select_related("guest", "room")
        if not is_admin(self.request.user):
            qs = qs.filter(user=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_admin"] = is_admin(self.request.user)
        ctx["pages"] = STATIC_PAGES
        return ctx


class ReservationDetailView(LoginRequiredMixin, DetailView):
    """Деталі бронювання. (В6.1)"""
    model = Reservation
    template_name = "hotel/booking_detail.html"
    context_object_name = "reservation"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not (is_admin(self.request.user) or obj.user_id == self.request.user.id):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pages"] = STATIC_PAGES
        ctx["is_admin"] = is_admin(self.request.user)
        return ctx


class ReservationCreateView(LoginRequiredMixin, CreateView):
    """
    Нове бронювання через ModelForm. Власник присвоюється у form_valid() — не у формі (В7.2).
    Перевизначення form_valid() (В6.4).
    """
    model = Reservation
    form_class = ReservationForm
    template_name = "hotel/booking_form.html"
    success_url = reverse_lazy("hotel:booking_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Звичайний користувач бачить лише доступні для нього номери
        if not is_admin(self.request.user):
            form.fields["room"].queryset = Room.objects.filter(
                status__in=["Available", "Occupied"]
            )
        return form

    def form_valid(self, form):
        # Отримуємо або створюємо гостя за email користувача (В7.2)
        reservation = form.save(commit=False)
        reservation.user = self.request.user  # власник — у form_valid, не у формі

        # Автоматично створюємо запис гостя з даних поточного користувача
        guest, _ = Guest.objects.get_or_create(
            email=self.request.user.email,
            defaults={"name": self.request.user.username},
        )
        reservation.guest = guest

        # Для денного бронювання check_out = check_in
        if reservation.stay_type == STAY_DAY:
            reservation.check_out = reservation.check_in

        try:
            reservation.full_clean()
            reservation.save()
            # Оновлюємо статус номера
            reservation.room.status = "Occupied"
            reservation.room.save(update_fields=["status"])
            messages.success(self.request, "Бронювання створено успішно.")
        except ValidationError as e:
            for field, errs in (e.message_dict.items() if hasattr(e, "message_dict") else {("__all__", e.messages)}.items()):
                for msg in errs:
                    form.add_error(field if field != "__all__" else None, msg)
            return self.form_invalid(form)

        return super(CreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Нове бронювання"
        ctx["pages"] = STATIC_PAGES
        return ctx


class ReservationUpdateView(LoginRequiredMixin, OwnerOrAdminMixin, UpdateView):
    """Редагування бронювання — лише власник або адмін. (В6.1, В7.3)"""
    model = Reservation
    form_class = ReservationForm
    template_name = "hotel/booking_form.html"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        reservation = form.save(commit=False)
        if reservation.stay_type == STAY_DAY:
            reservation.check_out = reservation.check_in
        try:
            reservation.full_clean()
            reservation.save()
            messages.success(self.request, "Бронювання оновлено.")
        except ValidationError as e:
            for field, errs in (e.message_dict.items() if hasattr(e, "message_dict") else {("__all__", e.messages)}.items()):
                for msg in errs:
                    form.add_error(field if field != "__all__" else None, msg)
            return self.form_invalid(form)
        return super(UpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Редагування бронювання"
        ctx["pages"] = STATIC_PAGES
        return ctx


class ReservationDeleteView(LoginRequiredMixin, OwnerOrAdminMixin, DeleteView):
    """Видалення бронювання — лише власник або адмін. (В6.1, В7.3)"""
    model = Reservation
    template_name = "hotel/booking_confirm_delete.html"
    success_url = reverse_lazy("hotel:booking_list")

    def form_valid(self, form):
        messages.success(self.request, "Бронювання скасовано.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pages"] = STATIC_PAGES
        return ctx


# ============================================================
# Номери: ListView + DetailView (В6.1)
# ============================================================

class RoomListView(ListView):
    """Каталог номерів з пагінацією. (В6.1, В6.3)"""
    model = Room
    template_name = "hotel/room_list.html"
    context_object_name = "rooms"
    paginate_by = 8

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("services")
        q = self.request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q as DQ
            qs = qs.filter(
                DQ(title__icontains=q) | DQ(location__icontains=q) | DQ(number__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["pages"] = STATIC_PAGES
        return ctx


class RoomDetailView(DetailView):
    """Деталі номера. (В6.1, В6.5 — маршрут із <int:pk>)"""
    model = Room
    template_name = "hotel/room_detail.html"
    context_object_name = "room"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["reviews"] = self.object.reviews.select_related("author")[:20]
        ctx["pages"] = STATIC_PAGES
        return ctx
