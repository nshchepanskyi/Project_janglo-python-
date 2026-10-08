-- 03_more_rooms.sql — ще 60 номерів для демо-бази GrandStay (запускати ПІСЛЯ 01_schema.sql і 02_seed.sql)
-- 20 × Single (103–122), 24 × Double (203–226), 16 × Suite (302–317)
-- Різні міста, ціни, рейтинги, місткість і набори послуг «що є в номері».
-- Скрипт безпечно запускати повторно: INSERT OR IGNORE не створює дублікатів (number — UNIQUE).
-- Поле photo порожнє — фото додаються пізніше через адмінку Django.

-- Каталог послуг (на випадок, якщо 02_seed.sql ще не запускали):
INSERT OR IGNORE INTO hotel_service (name, price) VALUES
    ('Breakfast', 10), ('Laundry', 15), ('Spa', 50), ('Airport Transfer', 25),
    ('Gym', 20), ('Pool', 15), ('Parking', 12), ('Room Service', 8),
    ('Mini Bar', 18), ('Dry Cleaning', 22), ('Conference Room', 100),
    ('Movie Rental', 12), ('Bicycle Rental', 30);

-- Номери:
INSERT OR IGNORE INTO hotel_room (number, room_type, price, status, title, location, capacity, rating, photo) VALUES
    ('103', 'Single', 50, 'Available', 'Cozy Single near Old Town', 'Lviv, Ukraine', 1, 4.4, ''),
    ('104', 'Single', 75, 'Available', 'Compact Single with Desk', 'Kyiv, Ukraine', 1, 4.5, ''),
    ('105', 'Single', 50, 'Available', 'Quiet Single with Courtyard View', 'Lviv, Ukraine', 1, 4.5, ''),
    ('106', 'Single', 65, 'Available', 'Modern Single Studio', 'Kharkiv, Ukraine', 1, 4.3, ''),
    ('107', 'Single', 35, 'Available', 'Budget Single Room', 'Dnipro, Ukraine', 1, 4.9, ''),
    ('108', 'Single', 60, 'Available', 'Single with Garden View', 'Chernivtsi, Ukraine', 1, 4.6, ''),
    ('109', 'Single', 55, 'Available', 'Minimalist Single Room', 'Kyiv, Ukraine', 1, 4.0, ''),
    ('110', 'Single', 55, 'Cleaning', 'Sunny Single by the Sea', 'Odesa, Ukraine', 1, 4.3, ''),
    ('111', 'Single', 75, 'Available', 'Business Single with Workspace', 'Kyiv, Ukraine', 1, 4.4, ''),
    ('112', 'Single', 50, 'Available', 'Traveler''s Single Room', 'Uzhhorod, Ukraine', 1, 4.6, ''),
    ('113', 'Single', 55, 'Available', 'Single with River View', 'Dnipro, Ukraine', 1, 4.9, ''),
    ('114', 'Single', 65, 'Available', 'Smart Single Room', 'Kharkiv, Ukraine', 1, 4.7, ''),
    ('115', 'Single', 60, 'Available', 'Retro Single in Historic House', 'Lviv, Ukraine', 1, 4.3, ''),
    ('116', 'Single', 60, 'Available', 'Single near Central Park', 'Vinnytsia, Ukraine', 1, 4.5, ''),
    ('117', 'Single', 55, 'Available', 'Calm Single with Reading Corner', 'Ivano-Frankivsk, Ukraine', 1, 4.5, ''),
    ('118', 'Single', 80, 'Maintenance', 'Single with Mountain View', 'Bukovel, Ukraine', 1, 3.8, ''),
    ('119', 'Single', 40, 'Available', 'Economy Single Room', 'Zaporizhzhia, Ukraine', 1, 4.3, ''),
    ('120', 'Single', 60, 'Available', 'Single Loft', 'Odesa, Ukraine', 1, 4.4, ''),
    ('121', 'Single', 75, 'Available', 'Urban Single Room', 'Kyiv, Ukraine', 1, 4.1, ''),
    ('122', 'Single', 60, 'Available', 'Single with Skyline View', 'Dnipro, Ukraine', 1, 4.7, ''),
    ('203', 'Double', 100, 'Available', 'Double with Sea View', 'Odesa, Ukraine', 2, 4.1, ''),
    ('204', 'Double', 100, 'Available', 'Family Double near Park', 'Kyiv, Ukraine', 2, 4.4, ''),
    ('205', 'Double', 105, 'Available', 'Elegant Double with Balcony', 'Lviv, Ukraine', 2, 4.8, ''),
    ('206', 'Double', 85, 'Available', 'Double Twin Room', 'Kharkiv, Ukraine', 2, 4.0, ''),
    ('207', 'Double', 120, 'Available', 'Premium Double with River View', 'Dnipro, Ukraine', 2, 4.9, ''),
    ('208', 'Double', 105, 'Available', 'Cozy Double in Old Town', 'Lviv, Ukraine', 2, 4.5, ''),
    ('209', 'Double', 95, 'Available', 'Double with Terrace', 'Odesa, Ukraine', 1, 4.1, ''),
    ('210', 'Double', 100, 'Available', 'Mountain Double with Fireplace', 'Bukovel, Ukraine', 2, 4.3, ''),
    ('211', 'Double', 110, 'Available', 'Business Double with Workspace', 'Kyiv, Ukraine', 2, 4.4, ''),
    ('212', 'Double', 65, 'Available', 'Romantic Double Room', 'Chernivtsi, Ukraine', 2, 4.6, ''),
    ('213', 'Double', 65, 'Available', 'Double with Garden Access', 'Uzhhorod, Ukraine', 1, 4.9, ''),
    ('214', 'Double', 95, 'Cleaning', 'Bright Double Studio', 'Vinnytsia, Ukraine', 2, 4.8, ''),
    ('215', 'Double', 130, 'Available', 'Double with City Panorama', 'Kyiv, Ukraine', 2, 4.4, ''),
    ('216', 'Double', 115, 'Available', 'Classic Double Room', 'Zaporizhzhia, Ukraine', 2, 4.8, ''),
    ('217', 'Double', 70, 'Available', 'Double near City Square', 'Ivano-Frankivsk, Ukraine', 2, 4.8, ''),
    ('218', 'Double', 115, 'Available', 'Modern Double Loft', 'Kharkiv, Ukraine', 1, 4.6, ''),
    ('219', 'Double', 95, 'Available', 'Double with Harbor View', 'Odesa, Ukraine', 2, 4.7, ''),
    ('220', 'Double', 90, 'Available', 'Designer Double Room', 'Lviv, Ukraine', 2, 4.6, ''),
    ('221', 'Double', 85, 'Maintenance', 'Double with Cathedral View', 'Kyiv, Ukraine', 1, 4.7, ''),
    ('222', 'Double', 95, 'Available', 'Quiet Double Room', 'Vinnytsia, Ukraine', 2, 4.1, ''),
    ('223', 'Double', 135, 'Available', 'Double with Ski Slope View', 'Bukovel, Ukraine', 2, 4.9, ''),
    ('224', 'Double', 80, 'Available', 'Spacious Double Room', 'Dnipro, Ukraine', 2, 4.1, ''),
    ('225', 'Double', 75, 'Available', 'Superior Double Room', 'Kharkiv, Ukraine', 2, 4.5, ''),
    ('226', 'Double', 95, 'Available', 'Double with Vineyard View', 'Uzhhorod, Ukraine', 1, 4.9, ''),
    ('302', 'Suite', 295, 'Available', 'Presidential Suite', 'Kyiv, Ukraine', 4, 4.8, ''),
    ('303', 'Suite', 235, 'Available', 'Royal Suite with Panorama', 'Lviv, Ukraine', 3, 4.8, ''),
    ('304', 'Suite', 315, 'Available', 'Family Suite with Two Bedrooms', 'Kyiv, Ukraine', 5, 4.7, ''),
    ('305', 'Suite', 240, 'Cleaning', 'Sea Breeze Suite', 'Odesa, Ukraine', 3, 4.9, ''),
    ('306', 'Suite', 195, 'Available', 'Executive Suite', 'Kharkiv, Ukraine', 2, 4.6, ''),
    ('307', 'Suite', 375, 'Available', 'Mountain Lodge Suite', 'Bukovel, Ukraine', 6, 4.7, ''),
    ('308', 'Suite', 205, 'Available', 'Honeymoon Suite', 'Chernivtsi, Ukraine', 2, 4.4, ''),
    ('309', 'Suite', 340, 'Available', 'Grand Family Suite', 'Dnipro, Ukraine', 6, 4.8, ''),
    ('310', 'Suite', 290, 'Maintenance', 'Penthouse Suite', 'Kyiv, Ukraine', 4, 5.0, ''),
    ('311', 'Suite', 285, 'Available', 'Old Town Heritage Suite', 'Lviv, Ukraine', 3, 4.6, ''),
    ('312', 'Suite', 275, 'Available', 'Business Suite with Meeting Room', 'Kyiv, Ukraine', 3, 4.6, ''),
    ('313', 'Suite', 255, 'Available', 'Garden Suite', 'Uzhhorod, Ukraine', 4, 4.9, ''),
    ('314', 'Suite', 300, 'Available', 'Seaside Penthouse', 'Odesa, Ukraine', 4, 4.8, ''),
    ('315', 'Suite', 250, 'Available', 'Luxury Suite with Fireplace', 'Ivano-Frankivsk, Ukraine', 4, 4.7, ''),
    ('316', 'Suite', 440, 'Available', 'Group Suite for Friends', 'Lviv, Ukraine', 8, 4.8, ''),
    ('317', 'Suite', 445, 'Available', 'Ski Chalet Suite', 'Bukovel, Ukraine', 8, 4.6, '');

-- «Що є в цьому номері»:
INSERT OR IGNORE INTO hotel_room_services (room_id, service_id)
SELECT r.id, s.id FROM hotel_room r JOIN hotel_service s
WHERE (r.number = '103' AND s.name IN ('Breakfast'))
   OR (r.number = '104' AND s.name IN ('Breakfast', 'Gym', 'Mini Bar', 'Bicycle Rental'))
   OR (r.number = '105' AND s.name IN ('Mini Bar'))
   OR (r.number = '106' AND s.name IN ('Breakfast', 'Laundry', 'Parking', 'Movie Rental'))
   OR (r.number = '107' AND s.name IN ('Parking', 'Mini Bar', 'Bicycle Rental'))
   OR (r.number = '108' AND s.name IN ('Mini Bar'))
   OR (r.number = '109' AND s.name IN ('Parking', 'Room Service', 'Bicycle Rental'))
   OR (r.number = '110' AND s.name IN ('Bicycle Rental'))
   OR (r.number = '111' AND s.name IN ('Bicycle Rental'))
   OR (r.number = '112' AND s.name IN ('Breakfast', 'Mini Bar', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '113' AND s.name IN ('Breakfast'))
   OR (r.number = '114' AND s.name IN ('Bicycle Rental'))
   OR (r.number = '115' AND s.name IN ('Laundry', 'Parking'))
   OR (r.number = '116' AND s.name IN ('Parking', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '117' AND s.name IN ('Breakfast', 'Laundry', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '118' AND s.name IN ('Gym', 'Bicycle Rental'))
   OR (r.number = '119' AND s.name IN ('Parking', 'Mini Bar'))
   OR (r.number = '120' AND s.name IN ('Parking', 'Room Service', 'Mini Bar', 'Bicycle Rental'))
   OR (r.number = '121' AND s.name IN ('Gym'))
   OR (r.number = '122' AND s.name IN ('Breakfast', 'Laundry', 'Gym'))
   OR (r.number = '203' AND s.name IN ('Breakfast', 'Laundry', 'Gym', 'Parking'))
   OR (r.number = '204' AND s.name IN ('Laundry', 'Room Service'))
   OR (r.number = '205' AND s.name IN ('Breakfast', 'Laundry', 'Spa', 'Parking', 'Room Service', 'Mini Bar'))
   OR (r.number = '206' AND s.name IN ('Breakfast', 'Airport Transfer', 'Gym', 'Pool', 'Dry Cleaning', 'Movie Rental'))
   OR (r.number = '207' AND s.name IN ('Laundry', 'Pool', 'Mini Bar', 'Dry Cleaning', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '208' AND s.name IN ('Breakfast', 'Pool', 'Room Service', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '209' AND s.name IN ('Airport Transfer', 'Parking', 'Room Service', 'Dry Cleaning'))
   OR (r.number = '210' AND s.name IN ('Laundry', 'Airport Transfer', 'Gym', 'Movie Rental'))
   OR (r.number = '211' AND s.name IN ('Breakfast', 'Laundry', 'Gym', 'Dry Cleaning'))
   OR (r.number = '212' AND s.name IN ('Airport Transfer', 'Pool', 'Room Service'))
   OR (r.number = '213' AND s.name IN ('Airport Transfer', 'Gym', 'Room Service'))
   OR (r.number = '214' AND s.name IN ('Breakfast', 'Spa', 'Airport Transfer', 'Mini Bar', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '215' AND s.name IN ('Parking', 'Mini Bar', 'Movie Rental'))
   OR (r.number = '216' AND s.name IN ('Gym', 'Pool', 'Parking', 'Movie Rental'))
   OR (r.number = '217' AND s.name IN ('Breakfast', 'Laundry', 'Airport Transfer', 'Room Service'))
   OR (r.number = '218' AND s.name IN ('Airport Transfer', 'Pool', 'Parking', 'Room Service', 'Movie Rental'))
   OR (r.number = '219' AND s.name IN ('Breakfast', 'Laundry', 'Spa', 'Pool', 'Mini Bar', 'Dry Cleaning'))
   OR (r.number = '220' AND s.name IN ('Laundry', 'Mini Bar'))
   OR (r.number = '221' AND s.name IN ('Laundry', 'Spa', 'Pool', 'Movie Rental'))
   OR (r.number = '222' AND s.name IN ('Laundry', 'Airport Transfer', 'Mini Bar', 'Movie Rental'))
   OR (r.number = '223' AND s.name IN ('Laundry', 'Airport Transfer', 'Room Service', 'Bicycle Rental'))
   OR (r.number = '224' AND s.name IN ('Breakfast', 'Airport Transfer', 'Gym', 'Parking', 'Room Service', 'Dry Cleaning'))
   OR (r.number = '225' AND s.name IN ('Airport Transfer', 'Parking'))
   OR (r.number = '226' AND s.name IN ('Parking', 'Room Service', 'Mini Bar', 'Dry Cleaning', 'Bicycle Rental'))
   OR (r.number = '302' AND s.name IN ('Breakfast', 'Spa', 'Airport Transfer', 'Pool', 'Room Service', 'Mini Bar', 'Bicycle Rental'))
   OR (r.number = '303' AND s.name IN ('Breakfast', 'Laundry', 'Spa', 'Gym', 'Room Service', 'Dry Cleaning', 'Conference Room'))
   OR (r.number = '304' AND s.name IN ('Breakfast', 'Laundry', 'Pool', 'Parking', 'Room Service', 'Conference Room'))
   OR (r.number = '305' AND s.name IN ('Breakfast', 'Spa', 'Gym', 'Parking', 'Room Service', 'Mini Bar', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '306' AND s.name IN ('Breakfast', 'Room Service', 'Conference Room', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '307' AND s.name IN ('Breakfast', 'Laundry', 'Gym', 'Pool', 'Room Service', 'Movie Rental'))
   OR (r.number = '308' AND s.name IN ('Breakfast', 'Spa', 'Airport Transfer', 'Pool', 'Room Service', 'Movie Rental', 'Bicycle Rental'))
   OR (r.number = '309' AND s.name IN ('Breakfast', 'Laundry', 'Pool', 'Parking', 'Room Service', 'Mini Bar', 'Dry Cleaning', 'Conference Room', 'Movie Rental'))
   OR (r.number = '310' AND s.name IN ('Breakfast', 'Airport Transfer', 'Gym', 'Room Service', 'Conference Room'))
   OR (r.number = '311' AND s.name IN ('Breakfast', 'Spa', 'Airport Transfer', 'Gym', 'Pool', 'Parking', 'Room Service', 'Conference Room'))
   OR (r.number = '312' AND s.name IN ('Breakfast', 'Spa', 'Gym', 'Pool', 'Parking', 'Room Service', 'Dry Cleaning', 'Conference Room'))
   OR (r.number = '313' AND s.name IN ('Breakfast', 'Parking', 'Room Service', 'Mini Bar', 'Conference Room'))
   OR (r.number = '314' AND s.name IN ('Breakfast', 'Pool', 'Parking', 'Room Service', 'Conference Room'))
   OR (r.number = '315' AND s.name IN ('Breakfast', 'Laundry', 'Spa', 'Airport Transfer', 'Gym', 'Pool', 'Parking', 'Room Service', 'Mini Bar', 'Conference Room'))
   OR (r.number = '316' AND s.name IN ('Breakfast', 'Laundry', 'Spa', 'Airport Transfer', 'Room Service', 'Dry Cleaning', 'Conference Room', 'Bicycle Rental'))
   OR (r.number = '317' AND s.name IN ('Breakfast', 'Laundry', 'Airport Transfer', 'Gym', 'Pool', 'Room Service', 'Dry Cleaning'));

-- Перевірка (необов'язково): SELECT COUNT(*) FROM hotel_room;  -- має бути 65
