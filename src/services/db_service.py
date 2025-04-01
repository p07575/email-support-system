import mysql.connector
from mysql.connector import pooling
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json
from ..config.settings import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, 
    MYSQL_PASSWORD, MYSQL_DATABASE
)

# Create a connection pool
db_config = {
    'host': MYSQL_HOST,
    'port': MYSQL_PORT,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE,
}

# Initialize the connection pool with a small set of connections
connection_pool = None

def initialize_db():
    """Initialize the database connection pool"""
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="email_support_pool",
            pool_size=5,
            **db_config
        )
        print(f"Database connection pool initialized: {MYSQL_HOST}:{MYSQL_PORT}")
        
        # Test the connection by getting a connection from the pool
        connection = connection_pool.get_connection()
        connection.close()
        return True
    except Exception as e:
        print(f"Error initializing database connection pool: {e}")
        return False

def get_connection():
    """Get a connection from the pool"""
    global connection_pool
    if connection_pool is None:
        initialize_db()
    return connection_pool.get_connection()

# Ticket functions
def save_ticket(ticket_id: str, from_email: str, subject: str, message: str, plain_message: str) -> bool:
    """Save a new ticket to the database"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        INSERT INTO tickets 
        (id, from_email, subject, message, plain_message, status) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (ticket_id, from_email, subject, message, plain_message, "received"))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"Error saving ticket to database: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False

def update_ticket_status(ticket_id: str, status: str) -> bool:
    """Update a ticket's status"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        query = "UPDATE tickets SET status = %s WHERE id = %s"
        cursor.execute(query, (status, ticket_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"Error updating ticket status: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False

def save_ticket_response(ticket_id: str, response_text: str) -> bool:
    """Save a response to a ticket"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        # Update the ticket status and response time
        ticket_query = "UPDATE tickets SET status = %s, response_time = %s WHERE id = %s"
        cursor.execute(ticket_query, ("responded", datetime.now(), ticket_id))
        
        # Save the response in the responses table
        response_query = "INSERT INTO responses (ticket_id, response_text) VALUES (%s, %s)"
        cursor.execute(response_query, (ticket_id, response_text))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"Error saving ticket response: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False

def get_ticket(ticket_id: str) -> Optional[Dict]:
    """Get a ticket by ID"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get the ticket
        ticket_query = "SELECT * FROM tickets WHERE id = %s"
        cursor.execute(ticket_query, (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            cursor.close()
            connection.close()
            return None
        
        # Get the latest response
        response_query = """
        SELECT response_text, sent_at 
        FROM responses 
        WHERE ticket_id = %s 
        ORDER BY sent_at DESC 
        LIMIT 1
        """
        cursor.execute(response_query, (ticket_id,))
        response = cursor.fetchone()
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for key, value in ticket.items():
            if isinstance(value, datetime):
                ticket[key] = value.isoformat()
        
        # Add the response data to the ticket
        if response:
            ticket['response'] = response['response_text']
            ticket['response_time'] = response['sent_at'].isoformat()
        
        cursor.close()
        connection.close()
        return ticket
    except Exception as e:
        print(f"Error getting ticket: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return None

def get_all_tickets() -> List[Dict]:
    """Get all tickets"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get all tickets sorted by received_at descending (newest first)
        query = "SELECT * FROM tickets ORDER BY received_at DESC"
        cursor.execute(query)
        tickets = cursor.fetchall()
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for ticket in tickets:
            for key, value in ticket.items():
                if isinstance(value, datetime):
                    ticket[key] = value.isoformat()
        
        cursor.close()
        connection.close()
        return tickets
    except Exception as e:
        print(f"Error getting all tickets: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return []

def get_recent_tickets(limit: int = 10) -> List[Dict]:
    """Get the most recent tickets"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get recent tickets sorted by received_at descending (newest first)
        query = "SELECT * FROM tickets ORDER BY received_at DESC LIMIT %s"
        cursor.execute(query, (limit,))
        tickets = cursor.fetchall()
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for ticket in tickets:
            for key, value in ticket.items():
                if isinstance(value, datetime):
                    ticket[key] = value.isoformat()
        
        cursor.close()
        connection.close()
        return tickets
    except Exception as e:
        print(f"Error getting recent tickets: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return []

# Database initialization and schema validation
def ensure_db_schema():
    """Ensure the database schema is properly set up"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        schema_valid = True
        
        if 'tickets' not in tables:
            print("tickets table not found, creating...")
            
            # Create tickets table
            cursor.execute("""
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
            )
            """)
            
            # Create index for faster retrieval
            cursor.execute("CREATE INDEX idx_tickets_status ON tickets(status)")
            cursor.execute("CREATE INDEX idx_tickets_received_at ON tickets(received_at)")
            
            schema_valid = False
        
        if 'responses' not in tables:
            print("responses table not found, creating...")
            
            # Create responses table
            cursor.execute("""
            CREATE TABLE responses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_id VARCHAR(30) NOT NULL,
                response_text LONGTEXT NOT NULL,
                sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            )
            """)
            
            schema_valid = False
        
        connection.commit()
        cursor.close()
        connection.close()
        
        if not schema_valid:
            print("Database schema has been initialized")
        
        return True
    except Exception as e:
        print(f"Error ensuring database schema: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False 