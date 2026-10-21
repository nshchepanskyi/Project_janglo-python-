PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hotel_room (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number VARCHAR(10) NOT NULL UNIQUE,
    room_type VARCHAR(20) NOT NULL DEFAULT 'Single'
        CHECK (room_type IN ('Single', 'Double', 'Suite')),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'Available'
        CHECK (status IN ('Available', 'Occupied', 'Cleaning', 'Maintenance')),
    title VARCHAR(120) NOT NULL DEFAULT '',
    location VARCHAR(120) NOT NULL DEFAULT '',
    capacity INTEGER NOT NULL DEFAULT 2
        CHECK (capacity >= 1
               AND ((room_type = 'Single' AND capacity <= 1)
                    OR (room_type = 'Double' AND capacity <= 2)
                    OR (room_type = 'Suite' AND capacity <= 8))),
    rating DECIMAL(2, 1) NOT NULL DEFAULT 4.5 CHECK (rating >= 0 AND rating <= 5),
    photo VARCHAR(100) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS hotel_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (price >= 0)
);

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
    user_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guests INTEGER NOT NULL DEFAULT 1 CHECK (guests >= 1),
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Checked-In', 'Checked-Out')),

    stay_type VARCHAR(10) NOT NULL DEFAULT 'Night'
        CHECK (stay_type IN ('Night', 'Day')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (stay_type = 'Night' AND check_out > check_in)
        OR (stay_type = 'Day' AND check_out = check_in)
    )
);

CREATE INDEX IF NOT EXISTS idx_reservation_guest ON hotel_reservation(guest_id);
CREATE INDEX IF NOT EXISTS idx_reservation_room ON hotel_reservation(room_id);
CREATE INDEX IF NOT EXISTS idx_reservation_user ON hotel_reservation(user_id);
CREATE INDEX IF NOT EXISTS idx_reservation_status ON hotel_reservation(status);

CREATE INDEX IF NOT EXISTS idx_reservation_dates ON hotel_reservation(check_in, check_out);

CREATE TABLE IF NOT EXISTS hotel_serviceorder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER NOT NULL REFERENCES hotel_guest(id) ON DELETE CASCADE,
    reservation_id INTEGER REFERENCES hotel_reservation(id) ON DELETE CASCADE,
    service_name VARCHAR(50) NOT NULL,
    service_price DECIMAL(10, 2) NOT NULL CHECK (service_price >= 0),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    total DECIMAL(10, 2) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    paid INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_serviceorder_guest ON hotel_serviceorder(guest_id);
CREATE INDEX IF NOT EXISTS idx_serviceorder_reservation ON hotel_serviceorder(reservation_id);
CREATE INDEX IF NOT EXISTS idx_serviceorder_status ON hotel_serviceorder(status);

CREATE TABLE IF NOT EXISTS hotel_roomfavorite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES hotel_room(id) ON DELETE CASCADE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, room_id)
);

CREATE INDEX IF NOT EXISTS idx_roomfavorite_room ON hotel_roomfavorite(room_id);

CREATE TABLE IF NOT EXISTS hotel_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL UNIQUE REFERENCES hotel_reservation(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES hotel_room(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    text TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_review_room ON hotel_review(room_id);
CREATE INDEX IF NOT EXISTS idx_review_user ON hotel_review(user_id);
