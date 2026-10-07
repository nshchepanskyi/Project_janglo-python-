-- 01_schema.sql — GrandStay Hotel, SQLite DDL (порт JSON-сховища Flet-версії на БД Django)
-- Таблиці відповідають моделям hotel/models.py: Room, Guest, Reservation, Service, ServiceOrder
-- + службові таблиці Django auth (User) для реєстрації/логіну (заміна auth.py + users.json)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hotel_room (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(10) NOT NULL UNIQUE,
    room_type VARCHAR(20) NOT NULL DEFAULT 'Single'
        CHECK (room_type IN ('Single', 'Double', 'Suite')),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'Available'
        CHECK (status IN ('Available', 'Occupied', 'Cleaning', 'Maintenance')),
    -- дані публічної картки (Фаза 1)
    title VARCHAR(120) NOT NULL DEFAULT '',
    location VARCHAR(120) NOT NULL DEFAULT '',
    capacity INTEGER NOT NULL DEFAULT 2
        -- місткість за типом: Single 1, Double 2, Suite до 8 (capacity_error)
        CHECK (capacity >= 1
               AND ((room_type = 'Single' AND capacity <= 1)
                    OR (room_type = 'Double' AND capacity <= 2)
                    OR (room_type = 'Suite' AND capacity <= 8))),
    rating DECIMAL(2, 1) NOT NULL DEFAULT 4.5 CHECK (rating >= 0 AND rating <= 5),
    -- шлях у media/ (ImageField, upload_to='rooms/')
    photo VARCHAR(100) NOT NULL DEFAULT ''
);

-- Каталог послуг у базі (модель Service): що є в номері + додаткові послуги
CREATE TABLE IF NOT EXISTS hotel_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (price >= 0)
);

-- «Що є в цьому номері»: галочки при додаванні номера (Room.services M2M)
CREATE TABLE IF NOT EXISTS hotel_room_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES hotel_room(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES hotel_service(id) ON DELETE CASCADE,
    UNIQUE (room_id, service_id)
);

CREATE TABLE IF NOT EXISTS hotel_guest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS hotel_reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER NOT NULL REFERENCES hotel_guest(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES hotel_room(id) ON DELETE RESTRICT,
    -- хто створив бронювання: для звичайного користувача — він сам;
    -- NULL для записів, створених до запровадження ролей (SET NULL)
    user_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guests INTEGER NOT NULL DEFAULT 1 CHECK (guests >= 1),
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Checked-In', 'Checked-Out')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (check_out > check_in)
);

CREATE INDEX IF NOT EXISTS idx_reservation_guest ON hotel_reservation(guest_id);
CREATE INDEX IF NOT EXISTS idx_reservation_room ON hotel_reservation(room_id);
CREATE INDEX IF NOT EXISTS idx_reservation_user ON hotel_reservation(user_id);
CREATE INDEX IF NOT EXISTS idx_reservation_status ON hotel_reservation(status);
-- швидкий пошук вільності: перетин інтервалів (check_in < other.check_out AND check_out > other.check_in)
CREATE INDEX IF NOT EXISTS idx_reservation_dates ON hotel_reservation(check_in, check_out);

CREATE TABLE IF NOT EXISTS hotel_serviceorder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER NOT NULL REFERENCES hotel_guest(id) ON DELETE CASCADE,
    -- до якого бронювання належить послуга (NULL — старі записи)
    reservation_id INTEGER REFERENCES hotel_reservation(id) ON DELETE CASCADE,
    service_name VARCHAR(50) NOT NULL,
    service_price DECIMAL(10, 2) NOT NULL CHECK (service_price >= 0),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    total DECIMAL(10, 2) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    -- оплата перед виселенням
    paid INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_serviceorder_guest ON hotel_serviceorder(guest_id);
CREATE INDEX IF NOT EXISTS idx_serviceorder_reservation ON hotel_serviceorder(reservation_id);
CREATE INDEX IF NOT EXISTS idx_serviceorder_status ON hotel_serviceorder(status);
