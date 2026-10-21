"""
E2E №1 — сценарій гостя.

Пошук номера на публічному сайті → сторінка місця → бронювання
(з авторизацією) → бронювання з'являється в «My Bookings» і в профілі.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from selenium.webdriver.common.by import By

from hotel.models import Reservation, Room

from .base import SeleniumLiveTestCase


class GuestBookingFlowTests(SeleniumLiveTestCase):
    """Гість знаходить вільний номер, бронює його та бачить бронювання у профілі."""

    def setUp(self):
        super().setUp()
        self.odesa = Room.objects.create(
            number="101", room_type="Double", price=Decimal("80"),
            title="Sea View", location="Odesa, Ukraine", capacity=2,
        )
        self.kyiv = Room.objects.create(
            number="202", room_type="Suite", price=Decimal("150"),
            title="City Loft", location="Kyiv, Ukraine", capacity=4,
        )
        self.guest_user = User.objects.create_user(
            "e2e_guest", "guest@example.com", "secret123",
        )
        self.check_in, self.check_out = self.future_dates(nights=3, offset=14)

    def test_guest_books_room_and_sees_it_in_profile(self):
        d = self.driver

        # --- 1. Головна сторінка: пошук номера в Одесі на 2 гостей ---
        self.open("/")
        self.wait_for_body("Find your next stay")
        self.fill("location", "Odesa")
        self.set_date("check_in", self.check_in.isoformat())
        self.set_date("check_out", self.check_out.isoformat())
        self.fill("guests", "2")
        self.click((By.CSS_SELECTOR, ".search-panel button[type=submit]"))

        self.wait_for_url("/places/")
        self.wait_for_body("Sea View")
        self.assertIn("location=Odesa", d.current_url)

        # фільтр спрацював: у каталозі лише одеський номер
        cards = d.find_elements(By.CSS_SELECTOR, ".place-card")
        self.assertEqual(len(cards), 1, "Очікували 1 номер за фільтром «Odesa»")
        self.assertIn("Sea View", cards[0].text)
        title_link = cards[0].find_element(By.CSS_SELECTOR, ".place-title")
        self.assertIn("/places/101/", title_link.get_attribute("href"))

        # --- 2. Сторінка місця: деталі, чек і кнопка Book ---
        self.click((By.CSS_SELECTOR, ".place-card .place-title"))
        self.wait_for_url("/places/101/")
        self.wait_for_body("Available for these dates")
        body = self.body_text()
        self.assertIn("Sea View", body)
        self.assertIn("#101", body)
        self.assertIn("Odesa, Ukraine", body)
        self.assertIn("$80.00", body)      # ціна за ніч
        self.assertIn("$240.00", body)      # 3 ночі × $80
        self.assertIn("$269.00", body)      # + сервісний збір 12% ($29)

        # --- 3. «Book» → гостя не авторизований → запит на вхід ---
        self.click((By.CSS_SELECTOR, ".pd-book a.btn.primary"))
        self.wait_for_url("/login/")
        self.wait_for_body("GrandStay Login")
        self.assertIn("next=", d.current_url)

        # --- 4. Вхід → повернення на форму бронювання з префілом ---
        self.fill("login", "e2e_guest")
        self.fill("password", "secret123")
        self.click((By.CSS_SELECTOR, "form button[type=submit]"))
        self.wait_for_url("/reservations/")
        self.wait_for_body("Book a Room")
        self.assertIn("room=101", d.current_url)
        self.assertIn("check_in=" + self.check_in.isoformat(), d.current_url)

        # префіл працює: номер, дати й кількість гостей уже вибрані
        self.assertEqual(
            self.element((By.NAME, "room_number")).get_attribute("value"), "101",
        )
        self.assertEqual(
            self.element((By.NAME, "check_in")).get_attribute("value"),
            self.check_in.isoformat(),
        )
        self.assertEqual(
            self.element((By.NAME, "check_out")).get_attribute("value"),
            self.check_out.isoformat(),
        )

        # --- 5. Заповнюємо й відправляємо форму бронювання ---
        self.fill("guest_name", "E2E Guest")
        self.fill("phone", "501234567")
        self.click((By.CSS_SELECTOR, "form.form-grid button[type=submit]"))

        self.assertIn("Reservation created", self.success_message())
        body = self.body_text()
        self.assertIn("101", body)
        self.assertIn("Pending", body)

        # --- 6. Дані реально збережені в БД ---
        res = Reservation.objects.get(room=self.odesa, user=self.guest_user)
        self.assertEqual(res.guest.name, "E2E Guest")
        self.assertEqual(res.guest.email, "guest@example.com")
        self.assertEqual(res.guests, 2)
        self.assertEqual(res.check_in, self.check_in)
        self.assertEqual(res.check_out, self.check_out)
        self.assertEqual(res.nights, 3)
        self.assertEqual(res.status, "Pending")
        self.odesa.refresh_from_db()       # статус номера синхронізовано сервером
        self.assertEqual(self.odesa.status, "Occupied")

        # --- 7. Профіль: бронювання видно гостю ---
        self.open("/profile/")
        self.wait_for_body("MY RESERVATIONS")
        body = self.body_text()
        kpi = self.wait_for_kpi(0, "1")     # MY RESERVATIONS
        self.assertEqual(kpi.text.strip(), "1")
        self.assertIn("101", body)
        self.assertIn(self.check_in.isoformat(), body)
