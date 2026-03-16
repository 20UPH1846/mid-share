-- ============================================================
-- MediShare Database Schema
-- Run this in MySQL: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS medishare;
USE medishare;

-- Users (donor / ngo / admin)
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(120) NOT NULL,
    email      VARCHAR(120) NOT NULL UNIQUE,
    phone      VARCHAR(20),
    address    TEXT,
    role       ENUM('donor','ngo','admin') NOT NULL DEFAULT 'donor',
    password   VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medicines donated
CREATE TABLE IF NOT EXISTS medicines (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    donor_id    INT NOT NULL,
    name        VARCHAR(200) NOT NULL,
    quantity    VARCHAR(100) NOT NULL,
    expiry_date DATE NOT NULL,
    description TEXT,
    photo       VARCHAR(255),
    status      ENUM('pending','approved','rejected') DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES users(id)
);

-- NGO requests
CREATE TABLE IF NOT EXISTS requests (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    ngo_id      INT NOT NULL,
    medicine_id INT NOT NULL,
    note        TEXT,
    status      ENUM('pending','approved','in_transit','delivered') DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ngo_id) REFERENCES users(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);

-- Default admin account (password: admin123)
INSERT IGNORE INTO users (name, email, phone, address, role, password)
VALUES (
    'Admin',
    'admin@medishare.com',
    '9999999999',
    'MediShare HQ',
    'admin',
    'pbkdf2:sha256:260000$rQ8LzJ$8b6e2c5d3f1a4e7b9c0d2f5a8e1b4c7d0f3a6e9b2c5d8f1a4e7b0c3d6f9a2e'
);
-- NOTE: After running schema, reset admin password via:
-- python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
-- Then: UPDATE users SET password='<hash>' WHERE email='admin@medishare.com';
