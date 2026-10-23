# GrandStay Hotel — Django-версія (порт з Flet)

Веб-сайт управління готелем: номери, бронювання, гості, послуги, дашборд.
**База даних:** PostgreSQL (Render PostgreSQL; локально SQLite).

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
- **Масове проставлення фото** — команда
  `python manage.py assign_room_photos` роздає файли з `media/rooms/`
  (`unsplash_*.jpg`) номерам **без повторів**: кожне фото йде рівно до
  одного номера, підбір іде за типом (Single → спальні, Double → спальні й
  вітальні, Suite → апартаменти з кухнею). Корисні прапорці:
  `--dry-run` (показати розподіл), `--use-numbered` (файл `101.jpg` → №101),
  `--keep-existing`, `--sequential`, `--pattern`. Файли не копіюються — у базі
  зберігається шлях `rooms/<файл>`.
- **Унікальність фото на рівні БД** — обмеження `room_photo_unique_per_room`
  (міграція `0009`): два номери не можуть мати одне й те саме фото; номери без
  фото (`photo = ''`) лишаються можливими.
- **Логотип на вкладці** — `hotel/static/hotel/favicon-180.png` (180×180),
  `favicon-32.png` (32×32) і `favicon.ico` для старих браузерів; підключені в
  `base_public.html` та на сторінках входу/реєстрації/підтвердження email.
  Маршрут `/favicon.ico` віддає логотип (браузери запитують його самі).
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

**Рекомендація номера електронною поштою:**
- На сторінці номера є посилання **Recommend this room by email**. Форма
  приймає ім'я та email відправника, email одержувача й необов'язковий коментар;
  одержувач отримує лист із повним посиланням на публічну сторінку номера.
- Листи надсилаються стандартним Django `send_mail()`. Локально вони
  друкуються в консоль; для доставки через SMTP задайте в `.env`
  `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`,
  `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` і
  `DEFAULT_FROM_EMAIL`. Пароль SMTP не зберігайте в коді.

**Підтвердження email при реєстрації:**
- Після реєстрації надсилається англомовний 6-символьний код (літери A–Z і
  цифри), дійсний 10 хвилин. До введення правильного коду акаунт неактивний;
  після підтвердження користувач автоматично входить і потрапляє на головну.
- Локально листи друкуються в консоль. Щоб вони приходили у справжню поштову
  скриньку, налаштуйте SMTP у `.env` за параметрами вище.

**Індекс пошуку доступності:**
- `Reservation.Meta.indexes` містить складений індекс
  `res_status_dates_room_idx` по `status`, `check_in`, `check_out`, `room`.
  Він відповідає фільтрам статусу та перетину дат у `search_rooms()` і
  `Reservation.clean()`; міграція `0008`.
- Щоб порівняти план і час пошуку без зміни реальних таблиць, виконайте
  `python manage.py benchmark_room_index --rows 100000 --runs 100`. Команда
  створює й видаляє тимчасову таблицю з синтетичними бронюваннями, показує
  час із/без індексу, коефіцієнт і план запиту. Результат залежить від СУБД,
  обсягу даних і вибраного діапазону дат. Локальний замір на SQLite
  (100 000 рядків, 100 запусків): **24.727 → 10.798 мс/запит (2.29×)**;
  план змінився зі сканування таблиці на використання індексу для обох гілок
  пошуку дат.

**Фаза 3 (нове): обране + відгуки (персоналізація гостя):**
- **Обране** — модель `RoomFavorite` (користувач ↔ номер, міграція `0006`,
  унікальна пара). Кнопка-зірочка ★/☆ на публічних картках і на сторінці
  місця: для залогіненого — POST-перемикач `/favorites/toggle/<number>/`,
  для аноніма — редирект на вхід з `?next=`. Сторінка **`/favorites/`**
  показує збережені картки; лічильник — у шапці поруч із меню.
- **Відгуки та рейтинг** — модель `Review` (автор, номер, бронювання,
  оцінка 1–5, текст, дата). Писати можна **лише після виселення**
  (Checked-Out) з конкретного номера і **лише одне повідомлення на
  бронювання** (`OneToOneField`) — чесна схема «гість реально жив у цьому
  номері». Форма відгуку зʼявляється на сторінці місця лише в того, хто
  вже виселився і ще не відгукнувся; відгуки публікуються там само.
  Середня оцінка **перетікає в `Room.rating`** (сигнали `post_save`/
  `post_delete` → `recalc_room_rating`) — зірочки на картках «живі».
  Модерація: `/admin/` бачить усі відгуки і може видаляти (рейтинг
  перераховується автоматично).
- **Два дрібні UX-фікси:** дати/гості з пошуку переносяться в лінки карток
  на сторінку місця (`{% querystring %}`), а форма бронювання має поле
  **Guests** (1–8, префіл `?guests=`, місткість перевіряє `Reservation.clean()`).
- Усе — серверними формами без JS; EN/UA та ₴/$ як і раніше.

**Профіль та телефонна версія (нове):**
- **Фото профілю** — модель `Profile` (OneToOne до `auth.User`, міграція
  `0007`; профіль створюється сигналом `post_save` при реєстрації). У
  `/profile/` — завантаження фото (до 2 МБ, перевірка Pillow у
  `Profile.clean()`: Django 6.x не валідує вміст ImageField на рівні моделі)
  та кнопка «Прибрати фото»; старий файл автоматично прибирається з
  `media/avatars/`. Фото показується в шапці сайту замість літери (без фото —
  літера, як і раніше) та на сторінці профілю. `Pillow` додано в
  `requirements.txt`; модель доступна в `/admin/` (Profile).
- **Телефонна версія** — медіа-запити ≤900/≤640/≤560px у `style.css` та
  `landing.css`: **бургер-меню** — на ≤900px кнопка-бургер у шапці відкриває
  висувну шухляду зліва з меню (Головна/Номери/… і адмін-меню теж), із
  півтемним оверлеєм; закриття — по оверлею, ESC або кліку по пункту
  (app.js `initBurger`; без JS нічого не ховається — меню лишається у шапці).
  Широкі таблиці (бронювання, номери, гості) гортаються вбік, форми стають
  в один стовпчик, сітки KPI/номерів — 2/1 колонка, auth-сторінки
  підлаштовуються під вузький екран; календар уже мав «нижній шит» із 560px.
  Кеш: `?v=6` для `landing.css`/`app.js`.

## Запуск

### 1. PostgreSQL

Встановіть PostgreSQL 17+ і створіть базу та користувача:

```bash
createuser --createdb janglo
createdb -U janglo janglo_hotel
```

### 2. Змінні оточення

Скопіюйте `.env.example` → `.env` і заповніть значення:

```bash
cp .env.example .env
```

Мінімальний вміст `.env`:

```
SECRET_KEY=your-secret-key-here
DB_ENGINE=django.db.backends.postgresql
DB_NAME=janglo_hotel
DB_USER=janglo
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
```

> Файл `.env` не потрапляє до репозиторію (`.gitignore`). У репозиторії зберігається лише `.env.example` з назвами змінних без значень.

### 3. Встановлення залежностей

```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 4. Міграції і тестові дані

```bash
python manage.py migrate
python manage.py createsuperuser   # адмін для /admin/ та /dashboard/
```

### 5. Запуск сервера

```bash
python manage.py runserver
```

Відкрити: http://127.0.0.1:8000/ (публічна головна),
http://127.0.0.1:8000/dashboard/ (потребує входу як staff/superuser).

**З телефона (LAN):** запусти сервер на всіх інтерфейсах і відкрий
його з телефона в тій самій Wi-Fi мережі:

```bash
python manage.py runserver 0.0.0.0:8000
```

Потім на телефоні: `http://<IP-ПК>:8000/` (IP — через `ipconfig` / `ifconfig`).

## Деплой на Render + PostgreSQL

Поточний сайт: **[grandstay-6kui.onrender.com](https://grandstay-6kui.onrender.com/)**.
Застосунок працює як Render Web Service, дані зберігаються в Render PostgreSQL
у регіоні Frankfurt. Налаштування Blueprint — у `render.yaml`.

### Налаштування

1. Створіть PostgreSQL у Render і розмістіть її в тому самому регіоні, що й Web
   Service. Для приватного з’єднання скопіюйте **Internal Database URL**.
2. Додайте його до Web Service як секретну змінну `DATABASE_URL`. Не зберігайте
   URL/пароль у Git і не публікуйте їх у скриншотах.
3. Задайте `SECRET_KEY` (Render може згенерувати значення) та `DEBUG=False`.
   Blueprint також налаштовує `DB_ENGINE=django.db.backends.postgresql`.
4. За потреби задайте `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` і
   `DJANGO_SUPERUSER_PASSWORD` для першого адміністратора. Після успішного
   створення акаунта видаліть ці три секрети з Environment.
5. Запуште зміни в GitHub і виконайте деплой. `build.sh` встановлює залежності,
   збирає статику, запускає `migrate`, завантажує demo-дані лише в порожню базу
   та створює адміністратора, якщо задані відповідні змінні.

Якщо підключення до БД не працює, перевірте, що `DATABASE_URL` — повний Internal
Database URL Render Postgres, і що база та вебсервіс розміщені у Frankfurt.
Локально можна продовжувати використовувати SQLite; `DATABASE_URL` має пріоритет,
коли заданий.

### Скриншоти актуального сайту

Знімки зроблено з розгорнутого сайту 2026-10-23:

| Сторінка | Скриншот |
|---|---|
| [Головна](https://grandstay-6kui.onrender.com/) | [`live-home.png`](data_text/screenshots/live-home.png) |
| [Каталог](https://grandstay-6kui.onrender.com/places/) | [`live-places.png`](data_text/screenshots/live-places.png) |
| [Номер 101](https://grandstay-6kui.onrender.com/places/101/) | [`live-room.png`](data_text/screenshots/live-room.png) |

Файли у `media/` з репозиторію доступні після деплою, але нові завантаження
користувачами потребують постійного файлового сховища (наприклад S3): локальна
файлова система Render не повинна використовуватися як довготривале сховище.

## Локалізація та валюта

- **Мова** перемикається кнопкою **EN/UA** у шапці (`/lang/`, сесія `lang`).
  Увесь текст (шаблони, повідомлення, помилки форм) іде через словник
  `hotel/l10n.py` (тег `{% tr %}` / функція `tr()`).
- **Валюта залежить від мови:** EN → **доларі `$`**, UA → **гривні `₴`**
  (конвертація `USD × USD_TO_UAH`, курс — у `hotel/currency.py`).
  У базі ціни зберігаються в USD, показуються через тег `{% money value N %}:
  `{% money res.amount 2 %}` → `$504.00` / `₴22,569.12`.
- Курс: зміни `USD_TO_UAH` у `hotel/currency.py`, якщо потрібен інший.

## Публічна частина (Фази 1–3)

| URL | Що це |
|---|---|
| `/` | головна: hero + панель пошуку + Recommended places + CTA |
| `/places/` | каталог/результати пошуку: `?location=&check_in=&check_out=&guests=` |
| `/places/<number>/` | **сторінка місця**: фото, деталі, чек і кнопка **Book · $…**; нижче — відгуки та форма (після виселення) |
| `/places/<number>/share/` | форма рекомендації номера електронною поштою |
| `/favorites/` | обрані номери (потребує вхіду) |
| `/favorites/toggle/<number>/` | POST-перемикач зірочки ★/☆ (анонім → вхід з `?next=`) |
| `/pages/terms/`, `/pages/privacy/`, `/pages/help/` | статичні сторінки футера |
| `/reservations/?room=101&check_in=...&check_out=...&guests=2` | кнопка **Book** з картки (після входу форма заповнена); `&stay=day` добирає денне бронювання |
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
  models.py        # Room, Guest, Reservation, Service, ServiceOrder, RoomFavorite,
                   # Review, Profile (фото профілю) + бізнес-логіка + search_rooms
                   # + сигнали: recalc_room_rating, створення профілю при реєстрації
  views.py         # dashboard, rooms, reservations, reservation_detail (додаткові послуги),
                   # guests, auth, lang/theme, home/places/place_detail/page/favorites (публічна частина)
  urls.py
  l10n.py          # словник EN/UK (порт з Flet)
  currency.py      # валюта: en → $, uk → ₴ (USD_TO_UAH)
  context_processors.py / templatetags/tr_tags.py  # мова і тема в шаблонах
  templates/hotel/ # base_public (спільна шапка+футер), base (успадковує її),
                    # home, places, place, share_room, email/share_room.txt, favorites,
                    # _place_card, _search_panel, page,
                    # dashboard, rooms, reservations, reservation, guests, login, register
  management/commands/benchmark_room_index.py  # план/швидкість індексу
  management/commands/assign_room_photos.py   # роздача фото з media/rooms номерам
  static/hotel/style.css    # адмінка: світла/темна тема + анімації
  static/hotel/landing.css  # публічна частина (зелений бренд) + зірочка/відгуки (Фаза 3)
  static/hotel/app.js       # лічильники KPI, прогрес-смуги
  sql/01_schema.sql, 02_seed.sql
  tests.py         # 111 тестів (PublicSiteTests, ServiceExtrasTests, PlaceDetailTests,
                    # RoomEmailRecommendationTests, ReservationAvailabilityIndexTests,
                    # RoomCapacityTests, AdjacentBookingTests, CurrencyLocalizationTests,
                   # CalendarWiringTests, DayStayTests, FavoritesReviewsTests,
                   # ProfileAvatarTests, MobileVersionTests, RoleAccessTests тощо)
e2e_tests/        # 2 E2E-тести в справжньому браузері (Chrome, Selenium) —
                   # окремий пакет поза застосунком, див. «E2E-тести» нижче
  base.py             # SeleniumLiveTestCase: живий сервер + Chrome + помічники
  test_guest_booking.py  # E2E №1: пошук → сторінка місця → бронювання → профіль
  test_admin_rooms.py    # E2E №2: адмін додає номер → він у публічному каталозі
```

## E2E-тести (Selenium)

Крім швидких юніт-тестів (`hotel/tests.py`, Django test-client) є два
E2E-тести, які проходять **через Selenium** у справжньому браузері Chrome:
живий сервер Django піднімається автоматично, сторінки відкриваються,
по кнопках реально клікають, а результат перевіряється і на екрані, і в БД.

Вони лежать в **окремій папці `e2e_tests/`** (поза застосунком `hotel`):

```
e2e_tests/
    base.py                # SeleniumLiveTestCase — база (живий сервер + Chrome + помічники)
    test_guest_booking.py  # E2E №1 — сценарій гостя
    test_admin_rooms.py    # E2E №2 — сценарій адміністратора
    README.md              # деталі та технічні нюанси
```

| Тест | Що перевіряє |
|---|---|
| `test_guest_booking.GuestBookingFlowTests.test_guest_books_room_and_sees_it_in_profile` | Сценарій гостя: пошук номера в Одесі на 2 гостей → сторінка місця (чек: 3 ночі × $80 + 12% збору = $269) → «Book» → вхід (з поверненням на форму за `?next=`) → бронювання → рядок у «My Bookings», KPI в профілі та запис у БД |
| `test_admin_rooms.AdminRoomManagementTests.test_admin_adds_room_and_it_appears_in_public_catalog` | Сценарій адміністратора: вхід → дашборд → «Rooms» → додавання номера (Suite, місткість 4, ціна $99, фото, послуга «Spa») → номер у адмін-таблиці та в публічному каталозі `/places/` |

### Запуск

```bash
# лише E2E-тести
python manage.py test e2e_tests -v 2

# усі тести разом (E2E включно)
python manage.py test e2e_tests hotel -v 2
```

Потрібен встановлений **Chrome**; `chromedriver` Selenium Manager завантажує
сам (вже є у кеші `~/.cache/selenium`).

**Браузер відкривається видимо** — тест сам заходить на потрібні сторінки
застосунку й клікає по кнопках, тож увесь сценарій видно на екрані.
Для CI або сервера без GUI — headless-режим:

```bash
set SELENIUM_HEADLESS=1        # Windows
```

Якщо Selenium Manager не зміг завантажити драйвер — вказати шлях уручну:

```bash
set CHROMEDRIVER_PATH=C:\\path\\to\\chromedriver.exe
```

### Технічні деталі

- `LiveServerTestCase` піднімає реальний HTTP-сервер; статика (CSS/JS)
  віддається через `staticfiles`-finders, тож тест бачить той самий
  фронтенд, що й користувач.
- Анімації появи (`fadeUp`) та «докручування» KPI-лічильників вимкнено
  для тестової вкладки — інакше Selenium читав би ще не підсумкове число.
- Поля `input[type=date]` заповнюються через DOM: нативне поле дат Chromium
  приймає текст у локалі браузера, тож це не залежить від locale.

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
