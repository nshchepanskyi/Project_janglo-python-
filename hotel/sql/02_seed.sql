-- 02_seed.sql — початкові дані (порт create_default_rooms + SERVICES_CATALOG з hotel_data.py)
-- Номери за замовчуванням: 101/102 Single $50, 201/202 Double $80, 301 Suite $150
-- + дані публічних карток (Фаза 1): назва, локація, місткість, рейтинг
-- Каталог послуг зберігається в коді (SERVICES_CATALOG), тут — довідка + демо-гість

INSERT OR IGNORE INTO hotel_room (number, room_type, price, status, title, location, capacity, rating) VALUES
    ('101', 'Single', 50, 'Available', 'Cozy Single with City View', 'Kyiv, Ukraine', 1, 4.6),
    ('102', 'Single', 50, 'Available', 'Bright Single Room', 'Kyiv, Ukraine', 1, 4.5),
    ('201', 'Double', 80, 'Available', 'Deluxe Double with Balcony', 'Kyiv, Ukraine', 2, 4.8),
    ('202', 'Double', 80, 'Available', 'Comfort Double Room', 'Kyiv, Ukraine', 2, 4.7),
    ('301', 'Suite', 150, 'Available', 'GrandStay Suite', 'Lviv, Ukraine', 3, 4.9);

-- Довідка: каталог послуг (ціни мають збігатися з SERVICES_CATALOG у models.py):
-- Breakfast 10, Laundry 15, Spa 50, Airport Transfer 25, Gym 20, Pool 15,
-- Parking 12, Room Service 8, Mini Bar 18, Dry Cleaning 22,
-- Conference Room 100, Movie Rental 12, Bicycle Rental 30
-- Сервісний збір публічного бронювання: SERVICE_FEE_RATE = 0.12 (12%, округлення до цілих $)
