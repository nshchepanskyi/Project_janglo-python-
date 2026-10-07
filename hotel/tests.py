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
