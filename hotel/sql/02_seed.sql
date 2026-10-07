-- 02_seed.sql — початкові дані (порт create_default_rooms + SERVICES_CATALOG з hotel_data.py)
-- Номери за замовчуванням: 101/102 Single $50, 201/202 Double $80, 301 Suite $150
-- Каталог послуг зберігається в коді (SERVICES_CATALOG), тут — довідка + демо-гість

INSERT OR IGNORE INTO hotel_room (number, room_type, price, status) VALUES
    ('101', 'Single', 50, 'Available'),
    ('102', 'Single', 50, 'Available'),
    ('201', 'Double', 80, 'Available'),
    ('202', 'Double', 80, 'Available'),
    ('301', 'Suite', 150, 'Available');

-- Довідка: каталог послуг (ціни мають збігатися з SERVICES_CATALOG у models.py):
-- Breakfast 10, Laundry 15, Spa 50, Airport Transfer 25, Gym 20, Pool 15,
-- Parking 12, Room Service 8, Mini Bar 18, Dry Cleaning 22,
-- Conference Room 100, Movie Rental 12, Bicycle Rental 30
