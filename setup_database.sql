-- Database setup for USSD Lightning Network application
-- Run this as MySQL root user

-- Create database
CREATE DATABASE IF NOT EXISTS ussd_lightning_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create application user
CREATE USER IF NOT EXISTS 'ussd_app'@'localhost' IDENTIFIED BY 'ussd_lightning_2024!';

-- Grant privileges
GRANT ALL PRIVILEGES ON ussd_lightning_db.* TO 'ussd_app'@'localhost';
FLUSH PRIVILEGES;

-- Use the database
USE ussd_lightning_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    balance BIGINT DEFAULT 0 COMMENT 'Balance in satoshis',
    language VARCHAR(5) DEFAULT 'en' COMMENT 'User language preference',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone_number)
);

-- Sessions table for USSD session management
CREATE TABLE IF NOT EXISTS ussd_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    current_menu VARCHAR(50) DEFAULT 'main',
    session_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 5 MINUTE),
    INDEX idx_session (session_id),
    INDEX idx_phone_session (phone_number),
    INDEX idx_expires (expires_at)
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    from_phone VARCHAR(20),
    to_phone VARCHAR(20),
    amount BIGINT NOT NULL COMMENT 'Amount in satoshis',
    transaction_type ENUM('send', 'receive', 'topup', 'withdraw') NOT NULL,
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    lightning_invoice VARCHAR(1000),
    payment_hash VARCHAR(100),
    invoice_id VARCHAR(100),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_from_phone (from_phone),
    INDEX idx_to_phone (to_phone),
    INDEX idx_payment_hash (payment_hash),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);

-- Lightning invoices table
CREATE TABLE IF NOT EXISTS lightning_invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id VARCHAR(100) UNIQUE NOT NULL,
    user_phone VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL COMMENT 'Amount in satoshis',
    payment_request TEXT,
    payment_hash VARCHAR(100),
    status ENUM('unpaid', 'paid', 'expired') DEFAULT 'unpaid',
    memo TEXT,
    expires_at TIMESTAMP,
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_user_phone (user_phone),
    INDEX idx_payment_hash (payment_hash),
    INDEX idx_status (status)
);

-- Insert demo users with balances
INSERT INTO users (phone_number, balance, language) VALUES
('+254712345678', 100000, 'en') ON DUPLICATE KEY UPDATE balance = VALUES(balance);

INSERT INTO users (phone_number, balance, language) VALUES
('+254787654321', 50000, 'sw') ON DUPLICATE KEY UPDATE balance = VALUES(balance);

INSERT INTO users (phone_number, balance, language) VALUES
('+254798765432', 75000, 'en') ON DUPLICATE KEY UPDATE balance = VALUES(balance);

-- Create a view for user balances (for MeTTa integration)
CREATE OR REPLACE VIEW user_balances AS
SELECT phone_number, balance, language, created_at, updated_at
FROM users;

-- Show created tables
SHOW TABLES;

-- Show user data
SELECT 'Demo Users:' as info;
SELECT phone_number, balance, language FROM users;