-- Xeren Progressive Car Showroom Relational Database Schema
-- Compatible with SQLite, PostgreSQL, and MySQL

CREATE TABLE IF NOT EXISTS vehicle_inventory (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    horsepower INTEGER NOT NULL,
    zero_to_sixty_sec DECIMAL(3, 2) NOT NULL,
    battery_range_km INTEGER NOT NULL,
    drive_type VARCHAR(50) DEFAULT 'AWD Tri-Motor',
    status VARCHAR(20) DEFAULT 'AVAILABLE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_drive_bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code VARCHAR(30) UNIQUE NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_email VARCHAR(150) NOT NULL,
    vehicle_model VARCHAR(100) NOT NULL,
    preferred_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Hypercar Models
INSERT INTO vehicle_inventory (model_name, category, base_price, horsepower, zero_to_sixty_sec, battery_range_km, drive_type)
VALUES 
    ('Xeren Apex Cyber-GT', 'Hypercar', 145000.00, 1450, 1.89, 850, 'AWD Quad-Motor'),
    ('Xeren Phantom Hyper-SUV', 'Luxury Performance SUV', 120000.00, 1200, 2.40, 780, 'AWD Tri-Motor'),
    ('Xeren Vision Speedster', 'Limited Track Special', 220000.00, 1800, 1.65, 920, 'Torque-Vectoring AWD');
