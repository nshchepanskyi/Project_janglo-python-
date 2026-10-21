"""
E2E-тести (Selenium) — окремий пакет поза застосунком `hotel`.

Структура:
    e2e_tests/
        base.py            — спільна база SeleniumLiveTestCase + помічники
        test_guest_booking.py — E2E №1: сценарій гостя (пошук → бронювання)
        test_admin_rooms.py   — E2E №2: сценарій адміністратора (номера → каталог)
        README.md          — як запускати

Запуск (див. README.md у цій папці):
    python manage.py test e2e_tests -v 2
"""
