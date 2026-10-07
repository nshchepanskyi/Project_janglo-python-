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
