from datetime import date

from django.core.exceptions import ValidationError
from django.forms import ModelForm, Form
from django import forms

from .models import (
    Guest,
    MAX_GUESTS,
    Reservation,
    Review,
    Room,
    ROOM_TYPES,
    STAY_NIGHT,
    STAY_DAY,
    STAY_TYPES,
)




def validate_future_date(value):
    """Дата повинна бути сьогодні або пізніше."""
    if value < date.today():
        raise ValidationError("Дата не може бути в минулому.")


def validate_phone(value):
    """Лише цифри, пробіли і знак +; мінімум 7 символів."""
    cleaned = value.replace(" ", "").replace("-", "")
    if cleaned and not cleaned.lstrip("+").isdigit():
        raise ValidationError("Номер телефону може містити лише цифри, +, пробіли і тире.")
    if cleaned and len(cleaned) < 7:
        raise ValidationError("Номер телефону занадто короткий (мінімум 7 символів).")




class GuestForm(ModelForm):
    """Форма гостя: ім'я, телефон, email. Без __all__."""

    phone = forms.CharField(
        required=False,
        validators=[validate_phone],
        label="Телефон",
        widget=forms.TextInput(attrs={"placeholder": "+380..."}),
    )

    class Meta:
        model = Guest
        fields = ["name", "phone", "email"]
        labels = {
            "name": "Повне ім'я",
            "email": "Email",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise ValidationError("Ім'я має містити щонайменше 2 символи.")
        if any(ch.isdigit() for ch in name):
            raise ValidationError("Ім'я не може містити цифри.")
        return name




class ReservationForm(ModelForm):
    """
    Форма бронювання: без полів user і guest — вони призначаються у form_valid().
    Поле room показується лише для адміністратора (у views.py).
    """

    check_in = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        validators=[validate_future_date],
        label="Дата заїзду",
    )
    check_out = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Дата виїзду",
    )

    class Meta:
        model = Reservation
        fields = ["room", "check_in", "check_out", "guests", "stay_type"]
        labels = {
            "room": "Номер",
            "guests": "Гостей",
            "stay_type": "Тип перебування",
        }

    def clean_guests(self):
        guests = self.cleaned_data.get("guests")
        if guests is not None and (guests < 1 or guests > MAX_GUESTS):
            raise ValidationError(
                f"Кількість гостей повинна бути від 1 до {MAX_GUESTS}."
            )
        return guests

    def clean(self):
        cleaned = super().clean()
        stay_type = cleaned.get("stay_type", STAY_NIGHT)
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")

        if stay_type == STAY_DAY:
            if check_in:
                cleaned["check_out"] = check_in
        else:
            if check_in and check_out and check_out <= check_in:
                raise ValidationError(
                    "Дата виїзду повинна бути пізніше дати заїзду."
                )
        return cleaned




class ReviewForm(ModelForm):
    """Форма відгуку: оцінка 1–5 + текст. Без reservation, room, author."""

    rating = forms.IntegerField(
        min_value=Review.RATING_MIN,
        max_value=Review.RATING_MAX,
        widget=forms.NumberInput(attrs={"min": 1, "max": 5}),
        label="Оцінка (1–5)",
    )

    class Meta:
        model = Review
        fields = ["rating", "text"]
        labels = {"text": "Коментар"}
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}

    def clean_text(self):
        text = self.cleaned_data.get("text", "").strip()
        if len(text) < 10:
            raise ValidationError(
                "Напишіть хоча б кілька слів (мінімум 10 символів)."
            )
        return text




class RoomSearchForm(Form):
    """Пошук номерів: локація, дати, кількість гостей, тип перебування."""

    location = forms.CharField(
        required=False,
        label="Місто або адреса",
        widget=forms.TextInput(attrs={"placeholder": "Kyiv, Paris..."}),
    )
    check_in = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Заїзд",
    )
    check_out = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Виїзд",
    )
    guests = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_GUESTS,
        label="Гостей",
        widget=forms.NumberInput(attrs={"min": 1, "max": MAX_GUESTS}),
    )
    stay_type = forms.ChoiceField(
        choices=[("", "Будь-який")] + STAY_TYPES,
        required=False,
        label="Тип перебування",
    )

    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        stay_type = cleaned.get("stay_type", "")

        if stay_type == STAY_DAY and check_in:
            cleaned["check_out"] = check_in
        elif check_in and check_out and check_out <= check_in:
            raise ValidationError(
                "Дата виїзду повинна бути пізніше дати заїзду."
            )
        return cleaned




class ShareRoomForm(Form):
    """Дані відправника й адресата для рекомендації сторінки номера."""

    name = forms.CharField(max_length=100, label="Your name")
    email = forms.EmailField(label="Your email")
    to = forms.EmailField(label="Recipient email")
    comments = forms.CharField(
        required=False,
        label="Additional comments",
        widget=forms.Textarea(attrs={"rows": 4}),
    )




class RoomForm(ModelForm):
    """Форма додавання/редагування номера для адміністратора."""

    class Meta:
        model = Room
        fields = ["number", "room_type", "title", "location", "price", "capacity", "status", "photo", "services"]
        labels = {
            "number": "Номер кімнати",
            "room_type": "Тип",
            "title": "Назва",
            "location": "Локація",
            "price": "Ціна за ніч ($)",
            "capacity": "Місткість (гостей)",
            "status": "Статус",
            "photo": "Фото",
            "services": "Послуги",
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise ValidationError("Ціна не може бути від'ємною.")
        return price

    def clean_number(self):
        number = self.cleaned_data.get("number", "").strip()
        if not number:
            raise ValidationError("Вкажіть номер кімнати.")
        return number
