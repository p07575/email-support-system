import sys
import os
import time
import threading
import signal
import atexit
from datetime import datetime
from typing import List, Dict

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import (
    EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_USERNAME, EMAIL_PASSWORD,
    EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT, EMAIL_CHECK_INTERVAL,
    OLLAMA_API_URL, OLLAMA_MODEL,
    DB_HOST, DB_NAME
)
from src.models.ticket import Ticket
from src.services.email_service import check_new_emails, send_email
from src.services.ollama_service import test_ollama_connection
from src.services.telegram_service import (
    initialize_telegram, 
    telegram_polling_loop, 
    forward_to_telegram,
    set_running_state
)
from src.services.db_service import (
    initialize_db,
    ensure_db_schema,
    save_ticket,
    update_ticket_status
)
from src.handlers.telegram_handlers import register_handlers

# Global state
running = True
email_thread = None
telegram_loop_thread = None

def handle_new_email(from_email: str, subject: str, body: str, plain_body: str, attachments: List[Dict] = None) -> None:
    """Handle a new email by creating a ticket and forwarding to Telegram"""
    # Generate ticket ID
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print("\n" + "="*50)
    print(f"HANDLING NEW EMAIL: {subject}")
    print(f"From: {from_email}")
    print(f"Body length: {len(body)} characters")
    
    # Detailed attachment debugging
    if attachments and len(attachments) > 0:
        print(f"📎 EMAIL HAS {len(attachments)} ATTACHMENT(S) 📎")
        for i, attachment in enumerate(attachments):
            print(f"  Attachment {i+1}: {attachment['filename']}")
            print(f"  Type: {attachment.get('content_type', 'unknown')}")
            print(f"  Size: {attachment.get('size', 0)} bytes")
            print(f"  Path: {attachment.get('path', 'unknown')}")
            
            # Check if file actually exists
            path = attachment.get('path', '')
            if path and os.path.exists(path):
                print(f"  File exists: ✅")
                # Verify file size
                actual_size = os.path.getsize(path)
                print(f"  Disk size: {actual_size} bytes")
            else:
                print(f"  File exists: ❌")
            print("  " + "-"*30)
    else:
        print("❌ NO ATTACHMENTS DETECTED IN EMAIL")
        print("This message was expected to have attachments (README.md)")
        print("Check the email message structure and attachment detection logic")
    
    print("="*50 + "\n")
    
    # Create new ticket and save to database
    success = save_ticket(ticket_id, from_email, subject, body, plain_body, attachments)
    if not success:
        print(f"Failed to save ticket #{ticket_id} to database")
        return
    
    # Send acknowledgment
    send_acknowledgment(from_email, ticket_id)
    
    # Forward to Telegram
    forward_to_telegram(ticket_id, from_email, subject, plain_body, attachments)

def send_acknowledgment(to_email: str, ticket_id: str) -> None:
    """Send an acknowledgment email to the customer"""
    html_content = f"""
    <h1>We've received your support request</h1>
    <p>Thank you for contacting us. Your support ticket (#{ticket_id}) has been created and our team will respond shortly.</p>
    <p>Please don't reply to this email as it's automatically generated.</p>
    """
    
    if send_email(to_email, f"Support Request Received - Ticket #{ticket_id}", html_content):
        update_ticket_status(ticket_id, "acknowledged")
        print(f"Sent acknowledgment for ticket #{ticket_id}")

def cleanup():
    """Clean up resources before exiting"""
    global running, email_thread, telegram_loop_thread
    
    print("\nCleaning up resources...")
    running = False
    set_running_state(False)  # Update Telegram service running state
    
    if email_thread and email_thread.is_alive():
        email_thread.join(timeout=5)
        
    if telegram_loop_thread and telegram_loop_thread.is_alive():
        telegram_loop_thread.join(timeout=5)
    
    print("Cleanup complete. Exiting.")

def start_background_tasks():
    """Start all background tasks"""
    global email_thread, telegram_loop_thread, running
    
    # Initialize the bot
    bot = initialize_telegram()
    set_running_state(True)  # Set Telegram service running state
    register_handlers(bot)
    
    # Reset the running flag
    running = True
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup(), sys.exit(0)))
    
    # Start email checking thread
    email_thread = threading.Thread(target=check_new_emails, args=(handle_new_email,), daemon=True)
    email_thread.start()
    
    # Start Telegram polling loop
    telegram_loop_thread = threading.Thread(target=telegram_polling_loop, daemon=True)
    telegram_loop_thread.start()

def main():
    """Main entry point for the application"""
    try:
        print("\n" + "="*50)
        print("📧 EMAIL SUPPORT SYSTEM STARTING 📧")
        print("="*50)
        print(f"IMAP Server: {EMAIL_IMAP_SERVER}:{EMAIL_IMAP_PORT}")
        print(f"SMTP Server: {EMAIL_SMTP_SERVER}:{EMAIL_SMTP_PORT}")
        print(f"Ollama Host: {OLLAMA_API_URL}")
        print(f"Ollama Model: {OLLAMA_MODEL}")
        print(f"Database: MySQL at {DB_HOST}/{DB_NAME}")
        print("="*50 + "\n")
        
        # Initialize and test database connection
        db_connection = initialize_db()
        if not db_connection:
            print("Failed to initialize database connection. Exiting.")
            return
            
        # Ensure database schema is set up
        schema_valid = ensure_db_schema()
        if not schema_valid:
            print("Failed to validate database schema. Exiting.")
            return
        
        # Test Ollama connection before starting
        ollama_available = test_ollama_connection()
        if not ollama_available:
            print("Warning: Ollama connection failed - responses will not be AI-processed")
        
        print("Starting background tasks...")
        
        # Start background tasks
        start_background_tasks()
        
        print("System running! Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        while running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        cleanup()
    except Exception as e:
        print(f"Unexpected error: {e}")
        cleanup()

if __name__ == "__main__":
    main()
    sys.exit(0) 