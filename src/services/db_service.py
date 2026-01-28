import mysql.connector
from mysql.connector import pooling
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json
from ..config.settings import (
    DB_HOST, DB_PORT, DB_USER, 
    DB_PASSWORD, DB_NAME
)

# Create a connection pool
db_config = {
    'host': DB_HOST,
    'port': DB_PORT,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'auth_plugin': 'caching_sha2_password',  # MySQL 8.0+ default auth
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
        print(f"Database connection pool initialized: {DB_HOST}:{DB_PORT}")
        
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
def save_ticket(ticket_id: str, from_email: str, subject: str, message: str, plain_message: str, attachments: List[Dict] = None) -> bool:
    """Save a new ticket to the database with optional attachments"""
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
        
        # Save attachments if any
        if attachments and len(attachments) > 0:
            print(f"Saving {len(attachments)} attachments for ticket #{ticket_id}")
            save_ticket_attachments(ticket_id, attachments)
        
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

def delete_ticket(ticket_id: str) -> bool:
    """Permanently delete a ticket and all related data (responses, attachments, drafts)"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        # Delete in order due to foreign key constraints
        # Delete draft responses
        cursor.execute("DELETE FROM draft_responses WHERE ticket_id = %s", (ticket_id,))
        
        # Delete responses
        cursor.execute("DELETE FROM responses WHERE ticket_id = %s", (ticket_id,))
        
        # Delete attachments
        cursor.execute("DELETE FROM attachments WHERE ticket_id = %s", (ticket_id,))
        
        # Delete the ticket itself
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"✅ Ticket {ticket_id} permanently deleted")
        return True
    except Exception as e:
        print(f"Error deleting ticket: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.rollback()
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
    """Get a ticket by ID with its attachments"""
    try:
        print(f"Fetching ticket #{ticket_id} from database")
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get the ticket
        ticket_query = "SELECT * FROM tickets WHERE id = %s"
        cursor.execute(ticket_query, (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            print(f"❌ Ticket #{ticket_id} not found in database")
            cursor.close()
            connection.close()
            return None
        
        print(f"✅ Found ticket #{ticket_id} in database")
        
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
        
        # Get attachments
        print(f"Fetching attachments for ticket #{ticket_id}")
        attachments_query = """
        SELECT id, filename, file_path, content_type, file_size 
        FROM attachments 
        WHERE ticket_id = %s
        """
        cursor.execute(attachments_query, (ticket_id,))
        attachments = cursor.fetchall()
        print(f"Found {len(attachments)} attachment(s) for ticket #{ticket_id}")
        
        # Convert datetime objects to ISO format strings for JSON serialization
        for key, value in ticket.items():
            if isinstance(value, datetime):
                ticket[key] = value.isoformat()
        
        # Add the response data to the ticket
        if response:
            ticket['response'] = response['response_text']
            ticket['response_time'] = response['sent_at'].isoformat()
        
        # Add attachments to the ticket
        ticket['attachments'] = attachments
        for i, attachment in enumerate(attachments):
            print(f"  Attachment {i+1}: {attachment['filename']} ({attachment.get('content_type', 'unknown')}, {attachment.get('file_size', 0)} bytes)")
            print(f"  File path: {attachment.get('file_path', 'unknown')}")
        
        cursor.close()
        connection.close()
        return ticket
    except Exception as e:
        print(f"❌ Error getting ticket: {e}")
        # Print the traceback for more detailed error information
        import traceback
        traceback.print_exc()
        
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

# Add a new function to save attachments
def save_ticket_attachments(ticket_id: str, attachments: List[Dict]) -> bool:
    """Save attachments for a ticket"""
    if not attachments:
        print(f"No attachments to save for ticket #{ticket_id}")
        return True
        
    print(f"Saving {len(attachments)} attachment(s) for ticket #{ticket_id}")
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        for i, attachment in enumerate(attachments):
            print(f"Saving attachment {i+1}/{len(attachments)}: {attachment['filename']}")
            query = """
            INSERT INTO attachments 
            (ticket_id, filename, file_path, content_type, file_size) 
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                ticket_id, 
                attachment['filename'], 
                attachment['path'], 
                attachment.get('content_type', 'application/octet-stream'),
                attachment.get('size', 0)
            ))
            print(f"✅ Attachment {i+1} saved to database: {attachment['filename']}")
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"All {len(attachments)} attachment(s) saved successfully for ticket #{ticket_id}")
        return True
    except Exception as e:
        print(f"❌ Error saving attachments: {e}")
        # Print the traceback for more detailed error information
        import traceback
        traceback.print_exc()
        
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False

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
            
        if 'attachments' not in tables:
            print("attachments table not found, creating...")
            
            # Create attachments table
            cursor.execute("""
            CREATE TABLE attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_id VARCHAR(30) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                content_type VARCHAR(100) NOT NULL,
                file_size INT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
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

# Add function to get attachments for a ticket
def get_ticket_attachments(ticket_id: str) -> List[Dict]:
    """Get all attachments for a ticket"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT id, filename, file_path, content_type, file_size 
        FROM attachments 
        WHERE ticket_id = %s
        """
        cursor.execute(query, (ticket_id,))
        attachments = cursor.fetchall()
        
        cursor.close()
        connection.close()
        return attachments
    except Exception as e:
        print(f"Error getting attachments: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return []


def save_draft_response(ticket_id: str, draft_text: str) -> bool:
    """Save a draft AI response for a ticket"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        # Check if drafts table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_id VARCHAR(30) NOT NULL UNIQUE,
                draft_text LONGTEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            )
        """)
        
        # Insert or update draft
        query = """
            INSERT INTO drafts (ticket_id, draft_text) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE draft_text = %s, updated_at = CURRENT_TIMESTAMP
        """
        cursor.execute(query, (ticket_id, draft_text, draft_text))
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"✅ Saved draft response for ticket #{ticket_id}")
        return True
    except Exception as e:
        print(f"❌ Error saving draft response: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False


def get_draft_response(ticket_id: str) -> Optional[str]:
    """Get the draft AI response for a ticket"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT draft_text FROM drafts WHERE ticket_id = %s"
        cursor.execute(query, (ticket_id,))
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if result:
            return result['draft_text']
        return None
    except Exception as e:
        print(f"Error getting draft response: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return None


def delete_draft_response(ticket_id: str) -> bool:
    """Delete the draft response for a ticket after it's been sent"""
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        query = "DELETE FROM drafts WHERE ticket_id = %s"
        cursor.execute(query, (ticket_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        print(f"Error deleting draft response: {e}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()
        return False 