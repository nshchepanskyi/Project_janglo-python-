from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    Guest,
    Reservation,
    Room,
    ServiceOrder,
    calc_reservation_revenue,
    calc_service_fee,
    calc_service_revenue,
    get_occupancy_rate,
    get_services_summary,
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
        for url in ["/dashboard/", "/rooms/", "/guests/", "/services/", "/profile/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_user_redirected_from_admin_pages_to_profile(self):
        self._login("ivan", "secret123")
        for url in ["/dashboard/", "/rooms/", "/guests/", "/services/"]:
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
