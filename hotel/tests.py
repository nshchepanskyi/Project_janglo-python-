import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import (
    Guest,
    Reservation,
    Review,
    Room,
    RoomFavorite,
    Service,
    ServiceOrder,
    calc_reservation_revenue,
    calc_service_fee,
    calc_service_revenue,
    get_occupancy_rate,
    get_services_summary,
    room_is_free,
    search_rooms,
)

# Тимчасове сховище для тестових завантажень фото
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="grandstay_test_media_")

# 1×1 GIF для тесту завантаження фото номера
TEST_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


class RoomModelTests(TestCase):
    def test_create_and_unique_number(self):
        Room.objects.create(number="101", room_type="Single", price=Decimal("50"))
        self.assertEqual(Room.objects.count(), 1)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Room.objects.create(number="101", room_type="Double", price=Decimal("80"))

    def test_occupancy_rate(self):
        Room.objects.create(number="101", room_type="Single", price=50, status="Available")
        Room.objects.create(number="102", room_type="Single", price=50, status="Occupied")
        self.assertEqual(get_occupancy_rate(), 50)


class ReservationFlowTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(number="201", room_type="Double", price=Decimal("80"))
        self.guest = Guest.objects.create(name="Test Guest", phone="+380000", email="t@t.com")

    def test_nights_and_amount(self):
        r = Reservation.objects.create(
            guest=self.guest, room=self.room,
            check_in=date(2026, 9, 1), check_out=date(2026, 9, 4),
        )
        self.assertEqual(r.nights, 3)
        self.assertEqual(r.amount, Decimal("240"))

    def test_check_out_must_be_later(self):
        r = Reservation(
            guest=self.guest, room=self.room,
            check_in=date(2026, 9, 4), check_out=date(2026, 9, 1),
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_revenue_helpers(self):
        Reservation.objects.create(
            guest=self.guest, room=self.room,
            check_in=date(2026, 9, 1), check_out=date(2026, 9, 3),
        )
        ServiceOrder.objects.create(
            guest=self.guest, service_name="Spa", service_price=Decimal("50"), quantity=2,
        )
        self.assertEqual(calc_reservation_revenue(), Decimal("160"))
        self.assertEqual(calc_service_revenue(), Decimal("100"))

    def test_services_summary(self):
        ServiceOrder.objects.create(
            guest=self.guest, service_name="Spa", service_price=Decimal("50"), quantity=2,
        )
        summary = get_services_summary()
        self.assertEqual(summary[0]["name"], "Spa")
        self.assertEqual(summary[0]["count"], 2)


class AuthPagesTests(TestCase):
    def test_register_login_flow(self):
        resp = self.client.post("/register/", {
            "username": "ivan", "email": "ivan@test.com",
            "password": "secret123", "confirm": "secret123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="ivan").exists())
        resp = self.client.post("/login/", {"login": "ivan", "password": "secret123"})
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)


class RoleAccessTests(TestCase):
    """Ролі: адмін керує всім, звичайний користувач бачить лише своє."""

    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@test.com", "pass1234")
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.user = User.objects.create_user("ivan", "ivan@test.com", "secret123")
        self.room = Room.objects.create(number="305", room_type="Double", price=Decimal("80"))

    def _login(self, username, password):
        self.client.login(username=username, password=password)

    def test_admin_can_open_admin_pages(self):
        self._login("boss", "pass1234")
        for url in ["/dashboard/", "/rooms/", "/guests/", "/reservations/", "/profile/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_user_redirected_from_admin_pages_to_profile(self):
        self._login("ivan", "secret123")
        for url in ["/dashboard/", "/rooms/", "/guests/"]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertTrue(resp.url.endswith("/profile/"), f"{url} -> {resp.url}")

    def test_login_redirects_by_role(self):
        resp = self.client.post("/login/", {"login": "boss", "password": "pass1234"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith("/dashboard/"))
        self.client.logout()
        resp = self.client.post("/login/", {"login": "ivan", "password": "secret123"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith("/profile/"))

    def test_user_sees_only_own_reservations(self):
        other = Guest.objects.create(name="Other Guest", phone="+380111", email="o@o.com")
        Reservation.objects.create(
            guest=other, room=self.room,
            check_in=date(2026, 9, 1), check_out=date(2026, 9, 3), user=self.admin,
        )
        self._login("ivan", "secret123")
        resp = self.client.get("/reservations/")
        self.assertEqual(len(resp.context["reservations"]), 0)
        self.assertFalse(resp.context["can_manage"])

        resp = self.client.post("/reservations/", {
            "action": "create", "guest_name": "Ivan Petrov",
            "country_code": "+380", "phone": "501112233",
            "email": "ivan@test.com", "room_number": "305",
            "check_in": "2026-10-20", "check_out": "2026-10-23",
        })
        self.assertEqual(resp.status_code, 302)
        own = Reservation.objects.filter(user=self.user)
        self.assertEqual(own.count(), 1)
        self.assertEqual(own.first().guest.name, "Ivan Petrov")

        resp = self.client.get("/reservations/")
        self.assertEqual(len(resp.context["reservations"]), 1)
        self.assertEqual(resp.context["reservations"][0].user, self.user)

    def test_user_cannot_change_reservation_status(self):
        guest = Guest.objects.create(name="Ivan Petrov", phone="+380501112233", email="ivan@test.com")
        res = Reservation.objects.create(
            guest=guest, room=self.room,
            check_in=date(2026, 10, 20), check_out=date(2026, 10, 23), user=self.user,
        )
        self._login("ivan", "secret123")
        resp = self.client.post("/reservations/", {
            "action": "status", "reservation_id": res.pk, "status": "Checked-In",
        })
        self.assertEqual(resp.status_code, 302)
        res.refresh_from_db()
        self.assertEqual(res.status, "Pending")
        self.assertEqual(Room.objects.get(pk=self.room.pk).status, "Available")

    def test_admin_can_change_reservation_status(self):
        guest = Guest.objects.create(name="Ivan Petrov", phone="+380501112233", email="ivan@test.com")
        res = Reservation.objects.create(
            guest=guest, room=self.room,
            check_in=date(2026, 10, 20), check_out=date(2026, 10, 23), user=self.user,
        )
        self._login("boss", "pass1234")
        self.client.post("/reservations/", {
            "action": "status", "reservation_id": res.pk, "status": "Checked-In",
        })
        res.refresh_from_db()
        self.assertEqual(res.status, "Checked-In")

    def test_profile_shows_own_stats(self):
        guest = Guest.objects.create(name="Ivan Petrov", phone="+380501112233", email="ivan@test.com")
        Reservation.objects.create(
            guest=guest, room=self.room,
            check_in=date(2026, 10, 20), check_out=date(2026, 10, 23), user=self.user,
        )
        ServiceOrder.objects.create(
            guest=guest, service_name="Spa", service_price=Decimal("50"), quantity=1,
        )
        self._login("ivan", "secret123")
        resp = self.client.get("/profile/")
        self.assertEqual(resp.status_code, 200)
        stats = resp.context["stats"]
        self.assertEqual(stats["my_reservations"], 1)
        self.assertEqual(stats["nights"], 3)
        self.assertEqual(stats["amount"], Decimal("240"))
        self.assertEqual(stats["orders"], 1)
        self.assertFalse(resp.context["is_admin"])


class PublicSiteTests(TestCase):
    """Публічний сайт (Фаза 1): головна, каталог, пошук з перевіркою вільності."""

    def setUp(self):
        self.single = Room.objects.create(
            number="101", room_type="Single", price=Decimal("50"),
            title="Cozy Single", location="Kyiv, Ukraine", capacity=1,
            rating=Decimal("4.6"),
        )
        self.double = Room.objects.create(
            number="201", room_type="Double", price=Decimal("80"),
            title="Deluxe Double", location="Lviv, Ukraine", capacity=2,
            rating=Decimal("4.8"),
        )
        self.suite = Room.objects.create(
            number="301", room_type="Suite", price=Decimal("150"),
            title="GrandStay Suite", location="Kyiv, Ukraine", capacity=3,
            rating=Decimal("4.9"),
        )
        guest = Guest.objects.create(name="Busy Guest", phone="+38000", email="b@b.com")
        # 201 зайнятий 10–13.09.2026
        Reservation.objects.create(
            guest=guest, room=self.double,
            check_in=date(2026, 9, 10), check_out=date(2026, 9, 13),
        )

    def test_home_is_public_and_shows_cards(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Recommended places")
        self.assertContains(resp, "Cozy Single")
        self.assertContains(resp, "search-panel")
        self.assertContains(resp, "Terms of Service")

    def test_search_by_location(self):
        resp = self.client.get("/places/", {"location": "Lviv"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([r.number for r in resp.context["rooms"]], ["201"])

    def test_search_filters_by_guests_capacity(self):
        resp = self.client.get("/places/", {"guests": "3"})
        self.assertEqual([r.number for r in resp.context["rooms"]], ["301"])

    def test_overlap_dates_exclude_busy_room(self):
        resp = self.client.get("/places/", {"check_in": "2026-09-12", "check_out": "2026-09-14"})
        numbers = [r.number for r in resp.context["rooms"]]
        self.assertNotIn("201", numbers)
        self.assertIn("101", numbers)
        self.assertIn("301", numbers)

    def test_adjacent_dates_are_free(self):
        # заїзд у день виїзду іншого гостя — не є перетином
        resp = self.client.get("/places/", {"check_in": "2026-09-13", "check_out": "2026-09-15"})
        self.assertIn("201", [r.number for r in resp.context["rooms"]])

    def test_invalid_date_order_shows_error(self):
        resp = self.client.get("/places/", {"check_in": "2026-09-14", "check_out": "2026-09-10"})
        self.assertEqual(resp.status_code, 200)
        msgs = [str(m) for m in resp.context["messages"]]
        self.assertIn("Check out must be later", msgs)
        # без фільтра дат показуємо весь каталог
        self.assertEqual(len(resp.context["rooms"]), 3)

    def test_bad_date_format_shows_error(self):
        resp = self.client.get("/places/", {"check_in": "not-a-date"})
        msgs = [str(m) for m in resp.context["messages"]]
        self.assertIn("Invalid date format", msgs)

    def test_static_footer_pages(self):
        for slug, title in [
            ("terms", "Terms of Service"),
            ("privacy", "Privacy Policy"),
            ("help", "Help Center"),
        ]:
            resp = self.client.get(f"/pages/{slug}/")
            self.assertEqual(resp.status_code, 200, slug)
            self.assertContains(resp, title)
        self.assertEqual(self.client.get("/pages/nope/").status_code, 404)

    def test_service_fee_and_total(self):
        # макет: $120 × 1 ніч + збір 12% ($14) = $134
        self.assertEqual(calc_service_fee(Decimal("120")), Decimal("14"))
        r = Reservation.objects.create(
            guest=Guest.objects.create(name="G", phone="+380", email="g@g.com"),
            room=self.suite, check_in=date(2026, 9, 1), check_out=date(2026, 9, 2),
        )
        self.assertEqual(r.amount, Decimal("150"))
        self.assertEqual(r.fee, Decimal("18"))
        self.assertEqual(r.total, Decimal("168"))

    def test_book_button_prefills_reservation_form(self):
        User.objects.create_user("buyer", "buyer@test.com", "secret123")
        self.client.login(username="buyer", password="secret123")
        resp = self.client.get("/reservations/", {
            "room": "201", "check_in": "2026-11-05", "check_out": "2026-11-07",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["prefill_room"], "201")
        self.assertEqual(resp.context["prefill_check_in"], "2026-11-05")
        self.assertContains(resp, 'value="201" selected')

    def test_login_returns_to_requested_page(self):
        User.objects.create_user("buyer", "buyer@test.com", "secret123")
        resp = self.client.post("/login/?next=/reservations/", {
            "login": "buyer", "password": "secret123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith("/reservations/"), resp.url)
        # приховане поле next у формі входу (після виходу)
        self.client.logout()
        resp = self.client.get("/login/?next=/places/")
        self.assertEqual(resp.context["next"], "/places/")

    def test_public_pages_work_in_ukrainian(self):
        self.client.get("/lang/")  # en → uk
        resp = self.client.get("/")
        self.assertContains(resp, "Рекомендовані місця")
        resp = self.client.get("/pages/terms/")
        self.assertContains(resp, "Умови користування")

    def test_new_room_card_fields(self):
        admin = User.objects.create_user("boss2", "boss2@test.com", "pass1234")
        admin.is_staff = True
        admin.save()
        self.client.login(username="boss2", password="pass1234")
        resp = self.client.post("/rooms/", {
            "action": "add", "number": "404", "room_type": "Suite",
            "price": "99", "title": "Sky Loft", "location": "Odesa, Ukraine",
            "capacity": "4",
        })
        self.assertEqual(resp.status_code, 302)
        r = Room.objects.get(number="404")
        self.assertEqual(r.title, "Sky Loft")
        self.assertEqual(r.location, "Odesa, Ukraine")
        self.assertEqual(r.capacity, 4)
        # картка без назві показує «Room X»
        r2 = Room.objects.create(number="405", room_type="Single", price=Decimal("40"))
        self.assertEqual(r2.display_title, "Room 405")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ServiceExtrasTests(TestCase):
    """Каталог послуг у БД, фото номерів, додаткові послуги та оплата перед виселенням."""

    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@test.com", "pass1234")
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.user = User.objects.create_user("ivan", "ivan@test.com", "secret123")
        self.room = Room.objects.create(number="410", room_type="Double", price=Decimal("80"))
        self.guest = Guest.objects.create(name="Ivan Petrov", phone="+38050", email="i@i.com")
        self.res = Reservation.objects.create(
            guest=self.guest, room=self.room,
            check_in=date(2026, 11, 1), check_out=date(2026, 11, 3), user=self.user,
        )

    def test_service_catalog_seeded_by_migration(self):
        """SERVICES_CATALOG перенесено з коду в таблицю hotel_service."""
        self.assertEqual(Service.objects.count(), 13)
        breakfast = Service.objects.get(name="Breakfast")
        self.assertEqual(breakfast.price, Decimal("10"))

    def test_services_tab_removed(self):
        """Вкладку Services прибрано — послуги живуть у базі даних."""
        self.assertEqual(self.client.get("/services/").status_code, 404)

    def test_add_room_with_photo_and_services(self):
        self.client.login(username="boss", password="pass1234")
        spa = Service.objects.get(name="Spa")
        resp = self.client.post("/rooms/", {
            "action": "add", "number": "909", "room_type": "Suite", "price": "120",
            "title": "Sky Loft", "location": "Odesa, Ukraine", "capacity": "3",
            "services": [str(spa.id)],
            "photo": SimpleUploadedFile("room.gif", TEST_GIF, content_type="image/gif"),
        })
        self.assertEqual(resp.status_code, 302)
        room = Room.objects.get(number="909")
        self.assertTrue(room.photo.name.startswith("rooms/"))
        self.assertEqual([s.name for s in room.services.all()], ["Spa"])

    def test_reservation_detail_access(self):
        # власник бронювання
        self.client.login(username="ivan", password="secret123")
        resp = self.client.get(f"/reservations/{self.res.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["res"], self.res)
        self.client.logout()
        # сторонній користувач потрапляє у профіль
        User.objects.create_user("other", "other@test.com", "secret123")
        self.client.login(username="other", password="secret123")
        resp = self.client.get(f"/reservations/{self.res.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith("/profile/"))
        self.client.logout()
        # адміністратор бачить будь-яке бронювання
        self.client.login(username="boss", password="pass1234")
        self.assertEqual(self.client.get(f"/reservations/{self.res.pk}/").status_code, 200)

    def test_order_extras_and_pay_before_checkout(self):
        self.client.login(username="ivan", password="secret123")
        spa = Service.objects.get(name="Spa")
        resp = self.client.post(f"/reservations/{self.res.pk}/", {
            "action": "add", "service": [str(spa.id)], f"qty_{spa.id}": "2",
        })
        self.assertEqual(resp.status_code, 302)
        order = ServiceOrder.objects.get(reservation=self.res)
        self.assertEqual(order.service_name, "Spa")
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.total, Decimal("100"))
        self.assertFalse(order.paid)
        # рахунок до сплати перед виселенням
        self.res.refresh_from_db()
        self.assertEqual(self.res.extras_due, Decimal("100"))
        self.assertEqual(self.res.extras_total, Decimal("100"))

        resp = self.client.post(f"/reservations/{self.res.pk}/", {"action": "pay"})
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.res.refresh_from_db()
        self.assertEqual(self.res.extras_due, 0)

    def test_checkout_blocked_until_extras_paid(self):
        ServiceOrder.objects.create(
            guest=self.guest, reservation=self.res,
            service_name="Spa", service_price=Decimal("50"), quantity=1,
        )
        self.client.login(username="boss", password="pass1234")
        # несплачені послуги блокують виселення
        self.client.post("/reservations/", {
            "action": "status", "reservation_id": self.res.pk, "status": "Checked-Out",
        })
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, "Pending")
        # оплатили — виселення проходить
        self.client.post(f"/reservations/{self.res.pk}/", {"action": "pay"})
        self.client.post("/reservations/", {
            "action": "status", "reservation_id": self.res.pk, "status": "Checked-Out",
        })
        self.res.refresh_from_db()
        self.assertEqual(self.res.status, "Checked-Out")


class PlaceDetailTests(TestCase):
    """Фаза 2: сторінка місця — чек із датами, вільність і кнопка «Забронювати · $»."""

    def setUp(self):
        self.room = Room.objects.create(
            number="501", room_type="Suite", price=Decimal("150"),
            title="Sky Loft", location="Kyiv, Ukraine", capacity=3,
            rating=Decimal("4.9"),
        )
        guest = Guest.objects.create(name="Busy Guest", phone="+38000", email="busy@b.com")
        # 501 зайнятий 10–13.12.2026
        Reservation.objects.create(
            guest=guest, room=self.room,
            check_in=date(2026, 12, 10), check_out=date(2026, 12, 13),
        )

    def test_detail_page_renders(self):
        resp = self.client.get("/places/501/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sky Loft")
        self.assertContains(resp, "Check availability")
        self.assertContains(resp, "per night")  # без дат — підсумок «за ніч»
        # без дат кнопка веде на форму бронювання з префілом
        self.assertContains(resp, 'href="/reservations/?room=501"')

    def test_unknown_room_is_404(self):
        resp = self.client.get("/places/999/")
        self.assertEqual(resp.status_code, 404)

    def test_check_math_dates_and_fee(self):
        resp = self.client.get("/places/501/", {
            "check_in": "2026-12-01", "check_out": "2026-12-04", "guests": "2",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["nights"], 3)
        self.assertEqual(resp.context["subtotal"], Decimal("450"))
        self.assertEqual(resp.context["fee"], Decimal("54"))
        self.assertEqual(resp.context["total"], Decimal("504"))
        self.assertContains(resp, "× 3 NIGHTS")
        self.assertContains(resp, "$504.00")
        self.assertContains(resp, "· $504")  # текст кнопки
        self.assertContains(resp, 'value="2026-12-01"')  # форма зберігає дати

    def test_busy_dates_hide_booking_button(self):
        resp = self.client.get("/places/501/", {
            "check_in": "2026-12-11", "check_out": "2026-12-12",
        })
        self.assertFalse(resp.context["room"].free)
        self.assertFalse(resp.context["can_book"])
        self.assertContains(resp, "Not available for these dates")
        self.assertNotContains(resp, 'href="/reservations/?room=501')

    def test_too_many_guests_blocks_booking(self):
        resp = self.client.get("/places/501/", {"guests": "5"})
        self.assertFalse(resp.context["fits"])
        self.assertFalse(resp.context["can_book"])
        self.assertContains(resp, "Too many guests for this room")

    def test_cards_link_to_detail_page(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'href="/places/501/"')
        resp = self.client.get("/places/")
        self.assertContains(resp, 'href="/places/501/"')

    def test_guests_input_on_place_page_limited_by_room_capacity(self):
        # місткість саме цього номера (Suite у фікстурі — 3), не глобальний максимум
        resp = self.client.get("/places/501/")
        self.assertContains(resp, 'name="guests" min="1" max="3"')
        resp = self.client.get("/places/501/", {"guests": "4"})
        self.assertFalse(resp.context["fits"])
        self.assertFalse(resp.context["can_book"])


class RoomCapacityTests(TestCase):
    """Перевірка місткості за типом: Single → 1, Double → 2, Suite → до 8."""

    def setUp(self):
        boss = User.objects.create_user("boss5", "boss5@test.com", "pass1234")
        boss.is_staff = True
        boss.save()
        self.client.login(username="boss5", password="pass1234")

    def _add(self, **data):
        payload = {
            "action": "add", "number": "700", "room_type": "Single",
            "price": "50", "title": "Test", "location": "Kyiv, Ukraine",
            "capacity": "1",
        }
        payload.update(data)
        return self.client.post("/rooms/", payload, follow=True)

    def test_single_rejects_two_guests(self):
        resp = self._add(number="701", capacity="2")
        self.assertContains(resp, "A Single room fits 1 guest")
        self.assertFalse(Room.objects.filter(number="701").exists())

    def test_double_rejects_three_guests(self):
        resp = self._add(number="702", room_type="Double", capacity="3")
        self.assertContains(resp, "A Double room fits 2 guests")
        self.assertFalse(Room.objects.filter(number="702").exists())

    def test_suite_rejects_nine_guests(self):
        resp = self._add(number="703", room_type="Suite", capacity="9")
        self.assertContains(resp, "A Suite room fits up to 8 guests")
        self.assertFalse(Room.objects.filter(number="703").exists())

    def test_suite_accepts_eight_guests(self):
        self._add(number="708", room_type="Suite", capacity="8")
        self.assertEqual(Room.objects.get(number="708").capacity, 8)

    def test_invalid_capacity_string(self):
        resp = self._add(number="709", capacity="abc")
        self.assertContains(resp, "Invalid capacity")
        self.assertFalse(Room.objects.filter(number="709").exists())

    def test_model_clean_blocks_wrong_capacity(self):
        room = Room(number="710", room_type="Single", price=Decimal("50"), capacity=3)
        with self.assertRaises(ValidationError):
            room.full_clean()

    def test_reservation_guests_limited_by_room_type(self):
        room = Room.objects.create(number="711", room_type="Single",
                                   price=Decimal("50"), capacity=1)
        guest = Guest.objects.create(name="Guest", phone="+380", email="g@g.com")
        res = Reservation(room=room, guest=guest, guests=2,
                          check_in=date(2026, 12, 1), check_out=date(2026, 12, 2))
        with self.assertRaises(ValidationError):
            res.full_clean()
        res.guests = 1
        res.full_clean()  # 1 гість у одномісному — ок

    def test_public_search_caps_guests_at_eight(self):
        resp = self.client.get("/", {"guests": "9"})
        self.assertEqual(resp.context["search"]["guests"], "8")
        self.assertEqual(resp.context["search"]["max_guests"], 8)

    def test_guests_input_limited_to_eight(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'max="8"')


class AdjacentBookingTests(TestCase):
    """Сусідні дати: виїзд одного гостя = заїзд іншого, накладання заборонене.

    Баг: після бронювання 10–15 число номера ставало Occupied і наступний
    гість не міг забронювати з 15-го, хоча дати не перетинаються.
    """

    def setUp(self):
        self.room = Room.objects.create(
            number="601", room_type="Double", price=Decimal("90"),
            title="Twin View", location="Lviv, Ukraine", capacity=2,
        )
        User.objects.create_user("buyer6", "buyer6@test.com", "secret123")
        self.client.login(username="buyer6", password="secret123")

    def _book(self, ci, co, email):
        return self.client.post("/reservations/", {
            "action": "create", "guest_name": "Guest One",
            "country_code": "+380", "phone": "501112233",
            "email": email, "room_number": "601",
            "check_in": ci, "check_out": co,
        })

    def test_adjacent_booking_is_allowed(self):
        # 10–15 листопада зайнято, з 15-го — вільно
        self._book("2026-11-10", "2026-11-15", "a1@test.com")
        self._book("2026-11-15", "2026-11-20", "a2@test.com")
        self.assertEqual(Reservation.objects.filter(room=self.room).count(), 2)

    def test_overlapping_booking_is_rejected(self):
        self._book("2026-11-10", "2026-11-15", "b1@test.com")
        self._book("2026-11-12", "2026-11-14", "b2@test.com")  # накладається
        self.assertEqual(Reservation.objects.filter(room=self.room).count(), 1)

    def test_model_clean_blocks_overlap(self):
        g1 = Guest.objects.create(name="A", phone="+3801", email="c1@t.com")
        Reservation.objects.create(
            guest=g1, room=self.room,
            check_in=date(2026, 11, 10), check_out=date(2026, 11, 15),
        )
        g2 = Guest.objects.create(name="B", phone="+3802", email="c2@t.com")
        res = Reservation(
            guest=g2, room=self.room,
            check_in=date(2026, 11, 14), check_out=date(2026, 11, 16),
        )
        with self.assertRaises(ValidationError):
            res.full_clean()
        # сусідні дати (заїзд у день виїзду) — проходять
        res.check_in = date(2026, 11, 15)
        res.full_clean()


class CurrencyLocalizationTests(TestCase):
    """Валюта: en → USD ($), uk → UAH (₴, конвертація за курсом USD_TO_UAH)."""

    def setUp(self):
        self.room = Room.objects.create(
            number="801", room_type="Suite", price=Decimal("150"),
            title="Rate Test", location="Kyiv, Ukraine", capacity=3,
            rating=Decimal("4.9"),
        )

    def test_money_str_helper(self):
        from .currency import money_str
        self.assertEqual(money_str("504", "en", 2), "$504.00")
        self.assertEqual(money_str("504", "en", 0), "$504")
        self.assertEqual(money_str("100", "uk", 0), "₴4,478")  # 100 × 44.78
        self.assertEqual(money_str("150", "uk", 2), "₴6,717.00")
        self.assertEqual(money_str(None, "en", 2), "$0.00")
        self.assertEqual(money_str("bad", "en", 2), "$0.00")

    def test_english_page_shows_dollars(self):
        resp = self.client.get("/places/801/", {
            "check_in": "2027-01-10", "check_out": "2027-01-13",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "$150.00")   # ціна за ніч
        self.assertContains(resp, "$450.00")   # 3 ночі
        self.assertContains(resp, "$504.00")   # + 12% збору
        self.assertNotContains(resp, "₴")

    def test_ukrainian_page_shows_hryvnias(self):
        self.client.get("/lang/")  # en → uk
        resp = self.client.get("/places/801/", {
            "check_in": "2027-01-10", "check_out": "2027-01-13",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "₴6,717.00")    # 150 × 44.78
        self.assertContains(resp, "₴20,151.00")   # 450 × 44.78
        self.assertContains(resp, "₴22,569.12")   # 504 × 44.78
        self.assertNotContains(resp, "$150.00")

    def test_ukrainian_catalog_and_card_prices(self):
        self.client.get("/lang/")
        resp = self.client.get("/places/")
        self.assertContains(resp, "₴6,717.00")   # картка номера
        resp = self.client.get("/")
        self.assertContains(resp, "₴6,717.00")   # рекомендовані на головній


class CalendarWiringTests(TestCase):
    """Красивий діапазонний календар (cal.js) підключений до всіх форм із датами."""

    def test_cal_js_is_bundled(self):
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find("hotel/cal.js"))

    def test_home_search_uses_custom_calendar(self):
        resp = self.client.get("/")
        self.assertContains(resp, "hotel/cal.js")
        self.assertContains(resp, 'class="js-cal"')
        self.assertContains(resp, 'name="check_in"')
        self.assertContains(resp, 'name="check_out"')

    def test_place_page_uses_custom_calendar(self):
        Room.objects.create(number="905", room_type="Single", price=Decimal("50"),
                            title="Cal Test", location="Kyiv, Ukraine")
        resp = self.client.get("/places/905/")
        self.assertContains(resp, 'class="js-cal"')

    def test_reservations_form_uses_custom_calendar(self):
        User.objects.create_user("caluser", "caluser@test.com", "secret123")
        self.client.login(username="caluser", password="secret123")
        resp = self.client.get("/reservations/")
        self.assertContains(resp, 'class="js-cal"')
        self.assertContains(resp, 'class="js-cal" required')  # обов'язковість переїжджає на кнопку


class DayStayTests(TestCase):
    """Денне бронювання (day use): заїзд о 07:00, виїзд о 23:59 того самого дня.

    Сценарій: гість приїхав зранку (зустріч увечері) і бронює номер лише на день.
    У базі зберігається одна дата (check_in == check_out), рахується 1 день.
    День займає весь календарний день: конфліктує з нічлігом, що накриває
    цю дату (включно з межами), та з іншим днем на ту саму дату.
    """

    def setUp(self):
        self.room = Room.objects.create(
            number="801", room_type="Double", price=Decimal("120"),
            title="Day Use Room", location="Kyiv, Ukraine", capacity=2,
        )
        self.user = User.objects.create_user("dayuser", "dayuser@test.com", "secret123")
        self.client.login(username="dayuser", password="secret123")
        self.guest = Guest.objects.create(
            name="Day Guest", phone="+380501112233", email="day@t.com",
        )

    def _day(self, d, save=False, user=None):
        """Денне бронювання на дату d (нічліговий двомісний номер 801)."""
        r = Reservation(
            guest=self.guest, room=self.room, stay_type="Day",
            check_in=d, check_out=d, user=user,
        )
        if save:
            r.save()
        return r

    # ---------- модель ----------
    def test_day_stay_is_one_day_amount(self):
        r = self._day(date(2026, 11, 5))
        r.full_clean()
        self.assertEqual(r.nights, 0)          # ночівлі немає
        self.assertEqual(r.days, 1)            # рахується 1 день
        self.assertEqual(r.amount, Decimal("120"))
        self.assertEqual(r.check_in_time, "07:00")
        self.assertEqual(r.check_out_time, "23:59")
        self.assertTrue(r.is_day_use)

    def test_day_stay_must_be_one_date(self):
        r = Reservation(
            guest=self.guest, room=self.room, stay_type="Day",
            check_in=date(2026, 11, 5), check_out=date(2026, 11, 6),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_night_stay_still_needs_later_checkout(self):
        r = Reservation(
            guest=self.guest, room=self.room, stay_type="Night",
            check_in=date(2026, 11, 5), check_out=date(2026, 11, 5),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    # ---------- накладання: день ↔ ніч ----------
    def test_day_conflicts_with_night_on_edges(self):
        # нічліг 10→15: день 10 (гість нічлігу заїжджає ввечері) і 15 (виїзд уранці)
        # теж зайняті — день триває 07:00–23:59
        Reservation.objects.create(
            guest=self.guest, room=self.room,
            check_in=date(2026, 11, 10), check_out=date(2026, 11, 15),
        )
        for d in (10, 12, 15):
            with self.assertRaises(ValidationError, msg=f"день {d} мусить бути зайнятий"):
                self._day(date(2026, 11, d)).full_clean()

    def test_day_free_outside_night_interval(self):
        Reservation.objects.create(
            guest=self.guest, room=self.room,
            check_in=date(2026, 11, 10), check_out=date(2026, 11, 15),
        )
        for d in (9, 16):  # 9-го гість нічлігу ще не заїхав, 16-го уже поїхав
            self._day(date(2026, 11, d)).full_clean()

    def test_night_conflicts_with_day_inside_interval(self):
        self._day(date(2026, 11, 12), save=True)
        for ci, co in ((11, 13), (12, 14), (10, 12)):  # нічліги, що накривають 12-те
            r = Reservation(
                guest=self.guest, room=self.room,
                check_in=date(2026, 11, ci), check_out=date(2026, 11, co),
            )
            with self.assertRaises(ValidationError, msg=f"{ci}→{co} мусить конфліктувати"):
                r.full_clean()
        # сусідні нічліги без 12-го — можна (заїзд у день виїзду дозволений)
        for ci, co in ((8, 11), (13, 15)):
            Reservation(
                guest=self.guest, room=self.room,
                check_in=date(2026, 11, ci), check_out=date(2026, 11, co),
            ).full_clean()

    # ---------- накладання: день ↔ день ----------
    def test_day_vs_day_same_date_conflicts(self):
        self._day(date(2026, 11, 5), save=True)
        with self.assertRaises(ValidationError):
            self._day(date(2026, 11, 5)).full_clean()
        self._day(date(2026, 11, 6)).full_clean()  # інший день — вільно

    # ---------- публічний пошук ----------
    def test_public_search_excludes_day_booking(self):
        self._day(date(2026, 11, 12), save=True)
        # день 12-го блокує нічліги, що його накривають (включно з межами)
        for ci, co in (("2026-11-10", "2026-11-13"), ("2026-11-12", "2026-11-14"),
                       ("2026-11-10", "2026-11-12")):
            rooms = search_rooms(check_in=date.fromisoformat(ci), check_out=date.fromisoformat(co))
            self.assertFalse(rooms.filter(pk=self.room.pk).exists(), f"{ci}→{co}")
        # інтервали без 12-го — вільні
        for ci, co in (("2026-11-08", "2026-11-11"), ("2026-11-13", "2026-11-15")):
            rooms = search_rooms(check_in=date.fromisoformat(ci), check_out=date.fromisoformat(co))
            self.assertTrue(rooms.filter(pk=self.room.pk).exists(), f"{ci}→{co}")

    def test_room_is_free_day_mode(self):
        self._day(date(2026, 11, 12), save=True)
        # нічний режим: перетини як і раніше
        self.assertFalse(room_is_free(self.room, date(2026, 11, 11), date(2026, 11, 13)))
        self.assertTrue(room_is_free(self.room, date(2026, 11, 8), date(2026, 11, 11)))
        # day-режим: достатньо лише однієї дати
        self.assertFalse(room_is_free(self.room, date(2026, 11, 12), None, stay_type="Day"))
        self.assertTrue(room_is_free(self.room, date(2026, 11, 11), None, stay_type="Day"))
        self.assertTrue(room_is_free(self.room, date(2026, 11, 13), None, stay_type="Day"))

    # ---------- форми / view ----------
    def test_form_shows_stay_type_select(self):
        resp = self.client.get("/reservations/")
        self.assertContains(resp, 'name="stay_type"')
        self.assertContains(resp, "Night stay")
        self.assertContains(resp, "Day stay (07:00–23:59)")
        self.assertContains(resp, 'class="night-only"')

    def test_day_booking_from_form_ignores_checkout(self):
        resp = self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "801",
            "stay_type": "Day", "check_in": "2026-11-05", "check_out": "2026-11-09",
        })
        self.assertEqual(resp.status_code, 302)
        res = Reservation.objects.get()
        self.assertEqual(res.stay_type, "Day")
        self.assertEqual(res.check_in, date(2026, 11, 5))
        self.assertEqual(res.check_out, date(2026, 11, 5))  # виїзд = заїзду
        self.assertEqual(res.amount, Decimal("120"))

    def test_day_booking_without_checkout_date(self):
        # у day-режимі поле виїзду можна лишити порожнім — сервер сам поставить дату
        self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "801",
            "stay_type": "Day", "check_in": "2026-11-05", "check_out": "",
        }, follow=True)
        res = Reservation.objects.get()
        self.assertEqual(res.check_out, date(2026, 11, 5))

    def test_night_booking_without_checkout_still_errors(self):
        resp = self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "801",
            "stay_type": "Night", "check_in": "2026-11-05", "check_out": "",
        }, follow=True)
        self.assertEqual(Reservation.objects.count(), 0)
        self.assertContains(resp, "Select check out date")

    def test_day_booking_blocks_night_booking(self):
        self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "801",
            "stay_type": "Day", "check_in": "2026-11-05", "check_out": "",
        })
        resp = self.client.post("/reservations/", {
            "action": "create", "guest_name": "Ivan", "country_code": "+380",
            "phone": "501112234", "email": "ivan@test.com", "room_number": "801",
            "stay_type": "Night", "check_in": "2026-11-04", "check_out": "2026-11-06",
        }, follow=True)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertContains(resp, "This room is already booked for the selected dates")

    def test_detail_page_shows_day_stay(self):
        res = self._day(date(2026, 11, 5), save=True, user=self.user)
        resp = self.client.get(f"/reservations/{res.pk}/")
        self.assertContains(resp, "Day stay")
        self.assertContains(resp, "07:00")
        self.assertContains(resp, "23:59")
        self.assertContains(resp, "× 1 DAY")  # рахунок: 1 день, а не 0 ночей

    def test_reservations_list_shows_day_marker(self):
        self._day(date(2026, 11, 5), save=True, user=self.user)
        resp = self.client.get("/reservations/")
        self.assertContains(resp, "07:00–23:59")
        self.assertContains(resp, ">DAY<")  # пігулка DAY замість діапазону дат

    def test_prefill_stay_day_selects_day_option(self):
        resp = self.client.get("/reservations/?stay=day")
        self.assertContains(resp, '<option value="Day" selected>')

    def test_ukrainian_day_use_texts(self):
        self._day(date(2026, 11, 5), save=True, user=self.user)
        self.client.get("/lang/")  # en → uk
        resp = self.client.get("/reservations/")
        self.assertContains(resp, "Денне бронювання (07:00–23:59)")
        self.assertContains(resp, "Нічне бронювання")
        self.assertContains(resp, "ДЕНЬ")


class FavoritesReviewsTests(TestCase):
    """Фаза 3: обране (зірочка) + відгуки після виселення з живим рейтингом."""

    def setUp(self):
        self.user = User.objects.create_user("oleh", "oleh@test.com", "secret123")
        self.other = User.objects.create_user("ivan", "ivan@test.com", "secret123")
        self.room = Room.objects.create(
            number="401", room_type="Double", price=Decimal("80"),
            title="Sunny Double", location="Kyiv, Ukraine", capacity=2,
            rating=Decimal("4.5"),
        )
        self.single = Room.objects.create(
            number="402", room_type="Single", price=Decimal("50"), capacity=1,
        )
        self.guest = Guest.objects.create(name="Oleh", phone="+38000", email="oleh@test.com")

    def _reservation(self, user=None, status="Checked-Out",
                     check_in=date(2026, 9, 1), check_out=date(2026, 9, 3)):
        return Reservation.objects.create(
            guest=self.guest, room=self.room, user=user or self.user,
            check_in=check_in, check_out=check_out, status=status,
        )

    # ---------- обране ----------

    def test_favorite_toggle_requires_login(self):
        resp = self.client.post("/favorites/toggle/401/", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/?next=", resp["Location"])
        self.assertEqual(RoomFavorite.objects.count(), 0)

    def test_favorite_toggle_add_and_remove(self):
        self.client.login(username="oleh", password="secret123")
        self.client.post("/favorites/toggle/401/", {"next": "/"})
        fav = RoomFavorite.objects.get()
        self.assertEqual(fav.user, self.user)
        self.assertEqual(fav.room, self.room)
        # другий клік — прибрати з обраного (toggle)
        self.client.post("/favorites/toggle/401/", {"next": "/"})
        self.assertEqual(RoomFavorite.objects.count(), 0)

    def test_favorites_page_requires_login(self):
        self.assertEqual(self.client.get("/favorites/").status_code, 302)

    def test_favorites_page_lists_saved_rooms(self):
        self.client.login(username="oleh", password="secret123")
        resp = self.client.get("/favorites/")
        self.assertContains(resp, "Your favorites will appear here")
        RoomFavorite.objects.create(user=self.user, room=self.room)
        RoomFavorite.objects.create(user=self.user, room=self.single)
        resp = self.client.get("/favorites/")
        self.assertContains(resp, "Sunny Double")
        self.assertContains(resp, "Room 402")

    def test_cards_show_star_and_header_counter(self):
        self.client.login(username="oleh", password="secret123")
        self.client.post("/favorites/toggle/401/")
        resp = self.client.get("/")
        # зірочка «в обраному» на картці 401 + лічильник у шапці
        self.assertContains(resp, "fav-star on")
        self.assertContains(resp, 'class="fav-count"')
        self.assertContains(resp, "Remove from favorites")

    # ---------- відгуки ----------

    def test_review_requires_checked_out_reservation(self):
        self.client.login(username="oleh", password="secret123")
        self._reservation(status="Pending")
        resp = self.client.post("/places/401/", {
            "action": "review", "reservation_id": Reservation.objects.get().pk,
            "rating": "5", "text": "Nice!",
        }, follow=True)
        self.assertContains(resp, "Only a checked-out guest can leave a review")
        self.assertEqual(Review.objects.count(), 0)

    def test_review_rejects_foreign_reservation(self):
        self._reservation(user=self.other)
        self.client.login(username="oleh", password="secret123")
        res = Reservation.objects.get()
        resp = self.client.post("/places/401/", {
            "action": "review", "reservation_id": res.pk,
            "rating": "5", "text": "Not mine",
        }, follow=True)
        self.assertContains(resp, "Only a checked-out guest can leave a review")
        self.assertEqual(Review.objects.count(), 0)

    def test_review_after_checkout_updates_room_rating(self):
        res = self._reservation()
        self.client.login(username="oleh", password="secret123")
        resp = self.client.post("/places/401/", {
            "action": "review", "reservation_id": res.pk,
            "rating": "5", "text": "Excellent stay!",
        }, follow=True)
        self.assertContains(resp, "Thank you for your review!")
        review = Review.objects.get()
        self.assertEqual(review.author, self.user)
        self.assertEqual(review.room, self.room)
        # середня оцінка перетікає в Room.rating (живі зірочки)
        self.room.refresh_from_db()
        self.assertEqual(self.room.rating, Decimal("5.0"))

    def test_one_review_per_reservation(self):
        res = self._reservation()
        self.client.login(username="oleh", password="secret123")
        post = {"action": "review", "reservation_id": res.pk,
                "rating": "5", "text": "Great!"}
        self.client.post("/places/401/", post)
        resp = self.client.post("/places/401/", post, follow=True)
        self.assertContains(resp, "You have already reviewed this stay")
        self.assertEqual(Review.objects.count(), 1)

    def test_review_rating_bounds(self):
        res = self._reservation()
        self.client.login(username="oleh", password="secret123")
        resp = self.client.post("/places/401/", {
            "action": "review", "reservation_id": res.pk,
            "rating": "9", "text": "Too good",
        }, follow=True)
        self.assertContains(resp, "Rating must be between 1 and 5")
        self.assertEqual(Review.objects.count(), 0)

    def test_review_delete_recalculates_rating(self):
        r1 = self._reservation(check_in=date(2026, 9, 1), check_out=date(2026, 9, 3))
        r2 = self._reservation(check_in=date(2026, 9, 5), check_out=date(2026, 9, 7))
        v1 = Review.objects.create(reservation=r1, room=self.room, author=self.user, rating=5, text="A")
        Review.objects.create(reservation=r2, room=self.room, author=self.user, rating=3, text="B")
        self.room.refresh_from_db()
        self.assertEqual(self.room.rating, Decimal("4.0"))
        v1.delete()  # так само працює видалення в /admin/
        self.room.refresh_from_db()
        self.assertEqual(self.room.rating, Decimal("3.0"))

    def test_place_page_shows_review_and_eligible_form(self):
        res = self._reservation()
        # форма відгуку показується лише після виселення
        self.client.login(username="oleh", password="secret123")
        resp = self.client.get("/places/401/")
        self.assertContains(resp, "Publish review")
        self.client.post("/places/401/", {
            "action": "review", "reservation_id": res.pk,
            "rating": "4", "text": "Cozy and clean",
        })
        resp = self.client.get("/places/401/")
        self.assertContains(resp, "Cozy and clean")
        self.assertNotContains(resp, "Publish review")  # вже відгукнувся

    # ---------- дрібні UX-фікси: дати з пошуку + гості у формі ----------

    def test_catalog_card_links_carry_dates(self):
        resp = self.client.get("/places/", {"check_in": "2026-10-01", "check_out": "2026-10-03"})
        self.assertContains(resp, "/places/401/?check_in=2026-10-01&amp;check_out=2026-10-03")
        # без дат у пошуку — чистий лінк без зайвого «?»
        resp = self.client.get("/places/")
        self.assertContains(resp, 'href="/places/401/"')

    def test_place_page_prefills_dates_and_guests_from_query(self):
        resp = self.client.get("/places/401/", {
            "check_in": "2026-10-01", "check_out": "2026-10-03", "guests": "2",
        })
        self.assertEqual(resp.context["search"]["check_in"], "2026-10-01")
        self.assertEqual(resp.context["search"]["guests"], "2")
        self.assertContains(resp, "&amp;guests=2")  # кнопка Book веде з гостями
        self.assertTrue(resp.context["fits"])       # 2 гостей у Double вміщує
        # однак для 5 гостей кнопка ховається
        resp = self.client.get("/places/401/", {
            "check_in": "2026-10-01", "check_out": "2026-10-03", "guests": "5",
        })
        self.assertFalse(resp.context["fits"])
        self.assertFalse(resp.context["can_book"])

    def test_booking_form_saves_guests(self):
        self.client.login(username="oleh", password="secret123")
        resp = self.client.get("/reservations/?room=401&guests=2")
        self.assertEqual(resp.context["prefill_guests"], 2)
        self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "401",
            "check_in": "2026-12-01", "check_out": "2026-12-03", "guests": "2",
        })
        res = Reservation.objects.get()
        self.assertEqual(res.guests, 2)

    def test_booking_form_guests_capacity_error(self):
        self.client.login(username="oleh", password="secret123")
        resp = self.client.post("/reservations/", {
            "action": "create", "guest_name": "Oleh", "country_code": "+380",
            "phone": "501112233", "email": "oleh@test.com", "room_number": "402",
            "check_in": "2026-12-01", "check_out": "2026-12-03", "guests": "2",
        }, follow=True)
        self.assertContains(resp, "A Single room fits 1 guest")
        self.assertEqual(Reservation.objects.count(), 0)
