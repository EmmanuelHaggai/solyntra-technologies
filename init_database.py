#!/usr/bin/env python3
"""
Initialize database for USSD Lightning Network application
"""
import os
import sys
from sqlalchemy import create_engine, text
from config import Config

def create_database():
    """Create database and tables if they don't exist"""
    try:
        # Connect to MySQL server (not specific database)
        server_url = Config.DATABASE_URL.rsplit('/', 1)[0]
        db_name = Config.DATABASE_URL.rsplit('/', 1)[1].split('?')[0]
        
        print(f"Connecting to MySQL server...")
        engine = create_engine(server_url + '/mysql')
        
        with engine.connect() as conn:
            # Create database if it doesn't exist
            print(f"Creating database '{db_name}' if it doesn't exist...")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            print(f"Database '{db_name}' ready")
        
        # Now connect to the specific database
        print(f"Connecting to database '{db_name}'...")
        engine = create_engine(Config.DATABASE_URL)
        
        with engine.connect() as conn:
            # Create users table
            print("Creating users table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    phone_number VARCHAR(20) UNIQUE NOT NULL,
                    balance BIGINT DEFAULT 0 COMMENT 'Balance in satoshis',
                    language VARCHAR(5) DEFAULT 'en' COMMENT 'User language preference',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_phone (phone_number)
                )
            """))
            
            # Create sessions table
            print("Creating sessions table...")
            conn.execute(text("""
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
                )
            """))
            
            # Create transactions table
            print("Creating transactions table...")
            conn.execute(text("""
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
                )
            """))
            
            # Insert demo users
            print("Creating demo users...")
            conn.execute(text("""
                INSERT INTO users (phone_number, balance, language) VALUES
                ('+254712345678', 100000, 'en'),
                ('+254787654321', 50000, 'sw'),
                ('+254798765432', 75000, 'en')
                ON DUPLICATE KEY UPDATE balance = VALUES(balance)
            """))
            
            conn.commit()
            print("Database initialization completed successfully!")
            
            # Verify data
            result = conn.execute(text("SELECT phone_number, balance FROM users"))
            print("\nDemo users:")
            for row in result:
                print(f"  {row[0]}: {row[1]} sats")
                
        return True
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)