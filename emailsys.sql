-- Email Support System database schema
-- Create this database with MySQL or MariaDB

CREATE DATABASE IF NOT EXISTS emailsys CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE emailsys;

-- Tickets table: stores incoming support requests
CREATE TABLE IF NOT EXISTS tickets (
    id VARCHAR(20) PRIMARY KEY,
    from_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    plain_message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'received',
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Responses table: stores responses to tickets
CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(20) NOT NULL,
    response_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attachments table: stores file attachments for tickets
CREATE TABLE IF NOT EXISTS attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    content_type VARCHAR(100),
    file_size INT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes for better performance
CREATE INDEX idx_ticket_status ON tickets (status);
CREATE INDEX idx_ticket_received_at ON tickets (received_at);
CREATE INDEX idx_responses_ticket_id ON responses (ticket_id);
CREATE INDEX idx_attachments_ticket_id ON attachments (ticket_id);
