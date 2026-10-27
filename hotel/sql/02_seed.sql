
INSERT OR IGNORE INTO hotel_room (number, room_type, price, status, title, location, capacity, rating, photo) VALUES
    ('101', 'Single', 50, 'Available', 'Cozy Single with City View', 'Kyiv, Ukraine', 1, 4.6, ''),
    ('102', 'Single', 50, 'Available', 'Bright Single Room', 'Kyiv, Ukraine', 1, 4.5, ''),
    ('201', 'Double', 80, 'Available', 'Deluxe Double with Balcony', 'Kyiv, Ukraine', 2, 4.8, ''),
    ('202', 'Double', 80, 'Available', 'Comfort Double Room', 'Kyiv, Ukraine', 2, 4.7, ''),
    ('301', 'Suite', 150, 'Available', 'GrandStay Suite', 'Lviv, Ukraine', 3, 4.9, '');

INSERT OR IGNORE INTO hotel_service (name, price) VALUES
    ('Breakfast', 10), ('Laundry', 15), ('Spa', 50), ('Airport Transfer', 25),
    ('Gym', 20), ('Pool', 15), ('Parking', 12), ('Room Service', 8),
    ('Mini Bar', 18), ('Dry Cleaning', 22), ('Conference Room', 100),
    ('Movie Rental', 12), ('Bicycle Rental', 30);

INSERT OR IGNORE INTO hotel_room_services (room_id, service_id)
SELECT r.id, s.id FROM hotel_room r JOIN hotel_service s
WHERE (r.number = '101' AND s.name IN ('Room Service', 'Laundry', 'Movie Rental'))
   OR (r.number = '102' AND s.name IN ('Room Service', 'Laundry'))
   OR (r.number = '201' AND s.name IN ('Breakfast', 'Gym', 'Room Service', 'Laundry'))
   OR (r.number = '202' AND s.name IN ('Breakfast', 'Gym', 'Room Service'))
   OR (r.number = '301' AND s.name IN ('Breakfast', 'Spa', 'Pool', 'Airport Transfer', 'Parking', 'Room Service'));

