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

## Запуск

```bash
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser   # опційно, для /admin/
py manage.py runserver
```

Відкрити: http://127.0.0.1:8000/ (публічна головна),
http://127.0.0.1:8000/dashboard/ (редірект на логін).

## Публічна частина (Фази 1–2)

| URL | Що це |
|---|---|
| `/` | головна: hero + панель пошуку + Recommended places + CTA |
| `/places/` | каталог/результати пошуку: `?location=&check_in=&check_out=&guests=` |
| `/places/<number>/` | **сторінка місця**: фото, деталі, чек і кнопка **Book · $…** |
| `/pages/terms/`, `/pages/privacy/`, `/pages/help/` | статичні сторінки футера |
| `/reservations/?room=101&check_in=...&check_out=...` | кнопка **Book** з картки (після входу форма заповнена) |
| `/reservations/<id>/` | сторінка бронювання: рахунок + додаткові послуги та оплата |

Правило вільності (`search_rooms` у `models.py`): номер вільний, якщо жодне
активне бронювання не перетинається з бажаним інтервалом
(`check_in < other.check_out AND check_out > other.check_in`).
Сервісний збір публічного бронювання — 12% (`SERVICE_FEE_RATE`).

Ліміт місткості за типом номера (`ROOM_CAPACITY_LIMITS`): **Single — 1 гість,
Double — 2, Suite — максимум 8**. Перевірка (`capacity_error`) діє в
`Room.clean()` (адмінка `/admin/`), у формі Add Room, у `Reservation.clean()`
(кількість гостей бронювання) та в полі Guests публічного пошуку
(`MAX_GUESTS = 8`).

## Структура

```
config/            # налаштування Django
hotel/             # застосунок готелю
  models.py        # Room, Guest, Reservation, Service, ServiceOrder + бізнес-логіка + search_rooms
  views.py         # dashboard, rooms, reservations, reservation_detail (додаткові послуги),
                   # guests, auth, lang/theme, home/places/place_detail/page (публічна частина)
  urls.py
  l10n.py          # словник EN/UK (порт з Flet)
  context_processors.py / templatetags/tr_tags.py  # мова і тема в шаблонах
  templates/hotel/ # base_public (спільна шапка+футер), base (успадковує її),
                   # home, places, place, _place_card, _search_panel, page,
                   # dashboard, rooms, reservations, reservation, guests, login, register
  static/hotel/style.css    # адмінка: світла/темна тема + анімації
  static/hotel/landing.css  # публічна частина (зелений бренд)
  static/hotel/app.js       # лічильники KPI, прогрес-смуги
  sql/01_schema.sql, 02_seed.sql
  tests.py         # 40 тестів (у т.ч. PublicSiteTests, ServiceExtrasTests, PlaceDetailTests)
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
