# E2E-тести (Selenium)

Тести, які проходять **через Selenium** у справжньому браузері Chrome.
На відміну від `hotel/tests.py` (швидкі юніт-тести через Django test-client)
тут реально відкриваються сторінки, по кнопках клікають, а результат
перевіряється і на екрані, і в базі даних.

## Структура

```
e2e_tests/
    base.py                # SeleniumLiveTestCase — база (сервер + Chrome + помічники)
    test_guest_booking.py  # E2E №1 — сценарій гостя
    test_admin_rooms.py    # E2E №2 — сценарій адміністратора
```

## Кейси

| Тест | Що перевіряє |
|---|---|
| `GuestBookingFlowTests.test_guest_books_room_and_sees_it_in_profile` | Пошук номера в Одесі на 2 гостей → сторінка місця (чек: 3 ночі × $80 + 12% збору = **$269**) → «Book» → вхід (повернення на форму за `?next=`) → бронювання → рядок у «My Bookings», KPI у профілі та запис у БД |
| `AdminRoomManagementTests.test_admin_adds_room_and_it_appears_in_public_catalog` | Вхід → дашборд → «Rooms» → додавання номера (Suite, місткість 4, ціна $99, **фото**, послуга «Spa») → номер в адмін-таблиці та в публічному каталозі `/places/` |

## Запуск

```bash
# лише E2E-тести
python manage.py test e2e_tests -v 2

# разом з юніт-тестами застосунку
python manage.py test e2e_tests hotel -v 2

# окремий кейс
python manage.py test e2e_tests.test_guest_booking -v 2
```

Потрібен встановлений **Chrome**; `chromedriver` Selenium Manager завантажує
сам (вже є у кеші `~/.cache/selenium`).

**Браузер відкривається видимо** — тест сам заходить на потрібні сторінки
застосунку й клікає по кнопках, тож увесь сценарій видно на екрані.
Тестовий сервер піднімається на випадковому порту (`LiveServerTestCase`),
адреса якого — `http://localhost:<порт>/`.

Для CI або сервера без GUI — headless-режим:

```bash
set SELENIUM_HEADLESS=1        # Windows
```

Якщо Selenium Manager не зміг завантажити драйвер — вказати шлях уручну:

```bash
set CHROMEDRIVER_PATH=C:\\path\\to\\chromedriver.exe
```

## Технічні деталі

- `LiveServerTestCase` піднімає реальний HTTP-сервер; статика (CSS/JS)
  віддається через `staticfiles`-finders, тож тест бачить той самий
  фронтенд, що й користувач.
- Якщо тест впав — зберігається скріншот браузера:
  `%TEMP%\grandstay_e2e_fail_<Клас>.png` (шляхalso друкується у виводі).
- Анімації появи (`fadeUp`) та «докручування» KPI-лічильників вимкнено
  для тестової вкладки — інакше Selenium читав би ще не підсумкове число.
- Поля `input[type=date]` заповнюються через DOM: нативне поле дат Chromium
  приймає текст у локалі браузера, тож це не залежить від locale.
- Очікування сторінок — за контентом (`wait_for_body`), а не лише за URL:
  після кліку DOM нового документа може ще парситись.
