"""
E2E №2 — сценарій адміністратора.

Вхід у панель керування → додавання номера (фото, послуги, місткість) →
номер зʼявляється в адмін-таблиці та в публічному каталозі.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from selenium.webdriver.common.by import By

from hotel.models import Room, Service

from .base import SeleniumLiveTestCase


class AdminRoomManagementTests(SeleniumLiveTestCase):
    """Адміністратор додає номер — і він одразу зʼявляється в публічному каталозі."""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            "e2e_admin", "admin@example.com", "admin12345",
        )
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()


        self.spa, _ = Service.objects.get_or_create(
            name="Spa", defaults={"price": Decimal("50")},
        )
        self.existing = Room.objects.create(
            number="101", room_type="Double", price=Decimal("80"),
            title="Sea View", location="Odesa, Ukraine", capacity=2,
        )

    def test_admin_adds_room_and_it_appears_in_public_catalog(self):
        d = self.driver


        self.login("e2e_admin", "admin12345")
        self.wait_for_url("/dashboard/")
        self.wait_for_body("Room Status")
        self.assertEqual(len(d.find_elements(By.CSS_SELECTOR, ".kpi-row .kpi")), 4)


        self.click((By.CSS_SELECTOR, '.p-nav a[href="/rooms/"]'))
        self.wait_for_url("/rooms/")
        self.wait_for_body("Add Room")


        self.fill("number", "777")
        self.fill("title", "Sky Loft")
        self.fill("location", "Kyiv, Ukraine")
        self.select("room_type", "Suite")
        self.fill("capacity", "4")
        self.fill("price", "99")


        self.element((By.NAME, "photo")).send_keys(self.photo_path)


        self.click((By.CSS_SELECTOR, f'input[name="services"][value="{self.spa.pk}"]'))

        self.click((By.CSS_SELECTOR, "form[enctype] button[type=submit]"))


        self.assertIn("Room 777 added", self.success_message())
        body = self.body_text()
        self.assertIn("777", body)
        self.assertIn("Sky Loft", body)
        self.assertIn("Suite", body)
        self.assertIn("Spa", body)


        new_room = Room.objects.get(number="777")
        self.assertEqual(new_room.title, "Sky Loft")
        self.assertEqual(new_room.location, "Kyiv, Ukraine")
        self.assertEqual(new_room.room_type, "Suite")
        self.assertEqual(new_room.capacity, 4)
        self.assertEqual(new_room.price, Decimal("99"))
        self.assertTrue(new_room.photo.name.startswith("rooms/"))
        self.assertEqual(list(new_room.services.all()), [self.spa])


        self.open("/places/?location=Kyiv")
        self.wait_for_body("Sky Loft")
        cards = d.find_elements(By.CSS_SELECTOR, ".place-card")
        self.assertEqual(len(cards), 1, "У каталозі має бути лише новий номер")
        self.assertIn("Sky Loft", cards[0].text)
        self.assertIn("$99.00", cards[0].text)
        self.assertIn("Kyiv, Ukraine", cards[0].text)
        self.assertIn("Spa", cards[0].text)
