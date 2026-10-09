# GrandStay Hotel — Django-версія (порт з Flet)

Веб-сайт управління готелем: номери, бронювання, гості, послуги, дашборд.
Порт десктоп-застосунку Flet (`Practic/`) на Django + SQLite.
**Фаза 1 (нове):** публічний сайт — головна з пошуком, каталог місць
з перевіркою вільності дат, картки з ціною/рейтингом/бейджем, статичні
сторінки футера (Terms/Privacy/Help).

**Фаза 2 (нове):** сторінка місця `/places/<number>/` — велике фото, деталі
номера, чипи послуг і **чек**: ціна × кількість ночей + сервісний збір 12%.
Дати/гостей міняємо прямо на сторінці (GET-форма, без JS) — чек
перераховується, вільність перевіряє `search_rooms`. Кнопка **Book · $269**
веде на форму бронювання з префілом; якщо номер зайнятий на обрані дати
або не вміщує стільки гостей — кнопка ховається з поясненням. Картки каталогу
(фото й назва) ведуть на сторінку місця, внизу — «Similar rooms».

**Фото та послуги (нове):**
- **Фото номерів** — `Room.photo` це `ImageField` (`media/rooms/…`), вантажиться
  формою «Add Room» (`enctype="multipart/form-data"`), показується на публічних
  картках і в списку номерів (плейсхолдер, якщо фото немає).
- **Каталог послуг у базі** — модель `Service` (таблиця `hotel_service`,
  наповнюється міграцією `0004` з `SERVICES_CATALOG`; редагується в `/admin/`).
  Вкладку Services прибрано з меню.
- **«Що є в цьому номері»** — галочки з каталогу при додаванні номера
  (`Room.services`, M2M `hotel_room_services`); чипи на картці та в списку.
- **Додаткові послуги перед виселенням** — на сторінці бронювання
  `/reservations/<id>/` гість замовляє послуги (кількість × ціна), бачить рядок
  «To pay before checkout» і сплачує кнопкою **Pay before checkout**
  (`ServiceOrder.paid`). Немає несплачених послуг → виселення (Checked-Out)
  заблоковане повідомленням.

**Денне бронювання (day use):**
- Гість приїхав зранку (зустріч увечері) і бронює номер **лише на день**:
  заїзд о **07:00**, виїзд о **23:59** того самого дня, без ночівлі.
  У базі — `Reservation.stay_type` (`Night`/`Day`, міграція `0005`) і одна
  дата: `check_out = check_in` (для `Day` це накладає ще й DB-free перевірка
  `clean()`: «A day stay is one day only»).
- **Форма `/reservations/`** має добір **Stay type** (Night stay /
  Day stay (07:00–23:59)). У day-режимі поле виїзду ховається
  (`.day-mode` ставить міні-JS в `app.js`) і сервер сам ставить
  `check_out = check_in`; без JS поле лишається видимим — можна вписати ту саму
  дату, бізнес-логіка живе на сервері. Префіл `?stay=day` одразу вмикає день.
- **Розрахунок:** `nights = 0` (ночівлі немає), `days = 1`, `amount = ціна × 1`;
  у чеку рядок «$120 × 1 DAY», години `07:00`/`23:59` у деталях і списках,
  пігулка **DAY** замість діапазону дат (список, профіль).
- **Правило вільності** (`conflict_q` у `models.py`): день D займає весь
  календарний день, тому конфліктує з нічлігом `[ci, co]` **включно з обома
  межами** (гість нічлігу заїжджає того вечора, а виїжджає вранці D), з іншим
  днем — лише на рівну дату; нічліг конфліктує з усіма днями в `[ci, co]`.
  Ніч-vs-ніч не змінився: сусідні дати дозволені. Хелпер використовують
  `clean()`, `search_rooms()`, `room_is_free()`.

## Запуск

```bash
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser   # опційно, для /admin/
py manage.py runserver
```

Відкрити: http://127.0.0.1:8000/ (публічна головна),
http://127.0.0.1:8000/dashboard/ (редірект на логін).

## Локалізація та валюта

- **Мова** перемикається кнопкою **EN/UA** у шапці (`/lang/`, сесія `lang`).
  Увесь текст (шаблони, повідомлення, помилки форм) іде через словник
  `hotel/l10n.py` (тег `{% tr %}` / функція `tr()`).
- **Валюта залежить від мови:** EN → **доларі `$`**, UA → **гривні `₴`**
  (конвертація `USD × USD_TO_UAH`, курс — у `hotel/currency.py`).
  У базі ціни зберігаються в USD, показуються через тег `{% money value N %}:
  `{% money res.amount 2 %}` → `$504.00` / `₴22,569.12`.
- Курс: зміни `USD_TO_UAH` у `hotel/currency.py`, якщо потрібен інший.

## Публічна частина (Фази 1–2)

| URL | Що це |
|---|---|
| `/` | головна: hero + панель пошуку + Recommended places + CTA |
| `/places/` | каталог/результати пошуку: `?location=&check_in=&check_out=&guests=` |
| `/places/<number>/` | **сторінка місця**: фото, деталі, чек і кнопка **Book · $…** |
| `/pages/terms/`, `/pages/privacy/`, `/pages/help/` | статичні сторінки футера |
| `/reservations/?room=101&check_in=...&check_out=...` | кнопка **Book** з картки (після входу форма заповнена); опційний `&stay=day` добирає денне бронювання |
| `/reservations/<id>/` | сторінка бронювання: рахунок + додаткові послуги та оплата |

Дати заїзду/виїзду вибираються **календарем** (`hotel/static/hotel/cal.js`,
підключається в `base_public.html`): перший клік — заїзд, другий — виїзд,
між ними підсвічується діапазон і рахуються ночі («5 ночей» / «5 nights»).
Мова береться з `<html lang>` (жовтень 2026 р. / October 2026), минулі дні
заблоковані, є «Сьогодні» і «Очистити». Він працює на всіх трьох формах
із датами: пошук, сторінка місця і `/reservations/`. Без JS поле
відкочується до нативного `input[type=date]` (прогресивний підхід).

Правило вільності (`search_rooms` / `room_is_free` у `models.py`, спільний
Q-хелпер `conflict_q`): для нічлігів номер вільний, якщо жодне активне
бронювання не перетинається з бажаним інтервалом
(`check_in < other.check_out AND check_out > other.check_in`), а **денне
бронювання** (07:00–23:59) конфліктує з нічлігом, що накриває цю дату
(включно з межами), та з іншим днем на ту саму дату.
Сервісний збір публічного бронювання — 12% (`SERVICE_FEE_RATE`).

Ліміт місткості за типом номера (`ROOM_CAPACITY_LIMITS`): **Single — 1 гість,
Double — 2, Suite — максимум 8**. Перевірка (`capacity_error`) діє в
`Room.clean()` (адмінка `/admin/`), у формі Add Room, у `Reservation.clean()`
(кількість гостей бронювання), а також у полі Guests: у публічному пошуку —
`MAX_GUESTS = 8`, на сторінці місця — місткість саме цього номера.

## Структура

```
config/            # налаштування Django
hotel/             # застосунок готелю
  models.py        # Room, Guest, Reservation, Service, ServiceOrder + бізнес-логіка + search_rooms
  views.py         # dashboard, rooms, reservations, reservation_detail (додаткові послуги),
                   # guests, auth, lang/theme, home/places/place_detail/page (публічна частина)
  urls.py
  l10n.py          # словник EN/UK (порт з Flet)
  currency.py      # валюта: en → $, uk → ₴ (USD_TO_UAH)
  context_processors.py / templatetags/tr_tags.py  # мова і тема в шаблонах
  templates/hotel/ # base_public (спільна шапка+футер), base (успадковує її),
                   # home, places, place, _place_card, _search_panel, page,
                   # dashboard, rooms, reservations, reservation, guests, login, register
  static/hotel/style.css    # адмінка: світла/темна тема + анімації
  static/hotel/landing.css  # публічна частина (зелений бренд)
  static/hotel/app.js       # лічильники KPI, прогрес-смуги
  sql/01_schema.sql, 02_seed.sql
  tests.py         # 79 тестів (PublicSiteTests, ServiceExtrasTests, PlaceDetailTests,
                   # RoomCapacityTests, AdjacentBookingTests, CurrencyLocalizationTests,
                   # CalendarWiringTests, DayStayTests, RoleAccessTests тощо)
```

## Відповідність Flet → Django

| Flet (`Practic/`) | Django (`hotel/`) |
|---|---|
| `hotel_data.py` (Room/Guest/Reservation/ServiceOrder, JSON) | `models.py` (ті ж сутності, SQLite + ORM) |
| `storage/*.json` | `db.sqlite3` + `sql/01_schema.sql`, `02_seed.sql` |
| `auth.py` | вбудований `django.contrib.auth` (хеш паролів) |
| `views/dashboard.py` | `views.dashboard_view` + `dashboard.html` |
| `views/rooms.py` | `views.rooms_view` + `rooms.html` |
| `views/reservations.py` | `views.reservations_view` + `reservations.html` |
| `views/guests.py` | `views.guests_view` + `guests.html` |
| `views/services.py` (окрема вкладка) | `Service` у БД: галочки в `rooms.html` + замовлення/оплата в `reservation_detail_view` |
| `views/login.py`, `register.py` | `login_view`, `register_view` |
| `l10n.py` (EN/UK) | `l10n.py` + сесія `lang` + тег `{% tr %}` |
| `theme.py` (light/dark) | сесія `theme` + CSS-змінні |
| `components/navbar.py`, `topbar.py` | `base_public.html` (шапка з меню за ролями + футер), `base.html` успадковує її для адмін-сторінок |

## Документація розділу 1

Локальна папка `Розділ 1/` (не в репозиторії): Вступ, 1.1–1.4, Висновок.
