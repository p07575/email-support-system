-- Email Support System Database Schema

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS email_support_system;
USE email_support_system;

-- Drop tables if they exist to avoid conflicts
DROP TABLE IF EXISTS responses;
DROP TABLE IF EXISTS tickets;

-- Create tickets table
CREATE TABLE tickets (
    id VARCHAR(30) PRIMARY KEY,
    from_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message LONGTEXT NOT NULL,
    plain_message LONGTEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'received',
    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_time DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create responses table for tracking responses to tickets
CREATE TABLE responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(30) NOT NULL,
    response_text LONGTEXT NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

-- Create index for faster retrieval
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_received_at ON tickets(received_at);

-- Sample test data (uncomment to use)
/*
INSERT INTO tickets (id, from_email, subject, message, plain_message, status, received_at)
VALUES 
('TKT-20250401001', 'test@example.com', 'Test Support Request', '<p>This is a test message</p>', 'This is a test message', 'received', NOW()),
('TKT-20250401002', 'another@example.com', 'Another Request', '<p>Another test message</p>', 'Another test message', 'forwarded_to_support', NOW());
*/
