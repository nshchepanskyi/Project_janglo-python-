# GrandStay Hotel — Django-версія (порт з Flet)

Веб-сайт управління готелем: номери, бронювання, гості, послуги, дашборд.
Порт десктоп-застосунку Flet (`Practic/`) на Django + SQLite.
**Фаза 1 (нове):** публічний сайт — головна з пошуком, каталог місць
з перевіркою вільності дат, картки з ціною/рейтингом/бейджем, статичні
сторінки футера (Terms/Privacy/Help).

## Запуск

```bash
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser   # опційно, для /admin/
py manage.py runserver
```

Відкрити: http://127.0.0.1:8000/ (публічна головна),
http://127.0.0.1:8000/dashboard/ (редірект на логін).

## Публічна частина (Фаза 1)

| URL | Що це |
|---|---|
| `/` | головна: hero + панель пошуку + Recommended places + CTA |
| `/places/` | каталог/результати пошуку: `?location=&check_in=&check_out=&guests=` |
| `/pages/terms/`, `/pages/privacy/`, `/pages/help/` | статичні сторінки футера |
| `/reservations/?room=101&check_in=...&check_out=...` | кнопка **Book** з картки (після входу форма заповнена) |

Правило вільності (`search_rooms` у `models.py`): номер вільний, якщо жодне
активне бронювання не перетинається з бажаним інтервалом
(`check_in < other.check_out AND check_out > other.check_in`).
Сервісний збір публічного бронювання — 12% (`SERVICE_FEE_RATE`).

## Структура

```
config/            # налаштування Django
hotel/             # застосунок готелю
  models.py        # Room, Guest, Reservation, ServiceOrder + бізнес-логіка + search_rooms
  views.py         # dashboard, rooms, reservations, guests, services, auth, lang/theme,
                   # home/places/page (публічна частина)
  urls.py
  l10n.py          # словник EN/UK (порт з Flet)
  context_processors.py / templatetags/tr_tags.py  # мова і тема в шаблонах
  templates/hotel/ # base_public (спільна шапка+футер), base (успадковує її),
                   # home, places, _place_card, _search_panel, page,
                   # dashboard, rooms, reservations, guests, services, login, register
  static/hotel/style.css    # адмінка: світла/темна тема + анімації
  static/hotel/landing.css  # публічна частина (зелений бренд)
  static/hotel/app.js       # лічильники KPI, прогрес-смуги
  sql/01_schema.sql, 02_seed.sql
  tests.py         # 28 тестів (у т.ч. PublicSiteTests)
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
| `views/services.py` | `views.services_view` + `services.html` |
| `views/login.py`, `register.py` | `login_view`, `register_view` |
| `l10n.py` (EN/UK) | `l10n.py` + сесія `lang` + тег `{% tr %}` |
| `theme.py` (light/dark) | сесія `theme` + CSS-змінні |
| `components/navbar.py`, `topbar.py` | `base_public.html` (шапка з меню за ролями + футер), `base.html` успадковує її для адмін-сторінок |

## Документація розділу 1

Локальна папка `Розділ 1/` (не в репозиторії): Вступ, 1.1–1.4, Висновок.
