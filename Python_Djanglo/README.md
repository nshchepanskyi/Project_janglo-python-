# GrandStay Hotel — Django-версія (порт з Flet)

Веб-сайт управління готелем: номери, бронювання, гості, послуги, дашборд.
Порт десктоп-застосунку Flet (`Practic/`) на Django + SQLite.

## Запуск

```bash
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser   # опційно, для /admin/
py manage.py runserver
```

Відкрити: http://127.0.0.1:8000/dashboard/ (редірект на логін).

## Структура

```
config/            # налаштування Django
hotel/             # застосунок готелю
  models.py        # Room, Guest, Reservation, ServiceOrder + SERVICES_CATALOG + бізнес-логіка
  views.py         # dashboard, rooms, reservations, guests, services, auth, lang/theme
  urls.py
  l10n.py          # словник EN/UK (порт з Flet)
  context_processors.py / templatetags/tr_tags.py  # мова і тема в шаблонах
  templates/hotel/ # base, dashboard, rooms, reservations, guests, services, login, register
  static/hotel/style.css  # світла/темна тема
  sql/01_schema.sql, 02_seed.sql
  tests.py
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
| `components/navbar.py`, `topbar.py` | `base.html` (sidebar + topbar) |

## Документація розділу 1

Локальна папка `../Розділ 1/` (не в репозиторії): Вступ, 1.1–1.4, Висновок.
