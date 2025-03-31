import sys
import os
import time
import threading
import signal
import atexit
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    IMAP_SERVER, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD,
    OLLAMA_HOST, OLLAMA_MODEL
)
from src.models.ticket import Ticket, ticket_queue
from src.services.email_service import check_new_emails, send_email
from src.services.ollama_service import test_ollama_connection
from src.services.telegram_service import initialize_telegram, telegram_polling_loop, forward_to_telegram
from src.handlers.telegram_handlers import register_handlers

# Global state
running = True
email_thread = None
telegram_loop_thread = None

def handle_new_email(from_email: str, subject: str, body: str, plain_body: str) -> None:
    """Handle a new email by creating a ticket and forwarding to Telegram"""
    # Generate ticket ID
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"New email received from {from_email}, Subject: {subject}")
    
    # Create new ticket
    ticket = Ticket(ticket_id, from_email, subject, body, plain_body)
    ticket_queue[ticket_id] = ticket
    
    # Send acknowledgment
    send_acknowledgment(from_email, ticket_id)
    
    # Forward to Telegram
    forward_to_telegram(ticket_id, from_email, subject, plain_body)

def send_acknowledgment(to_email: str, ticket_id: str) -> None:
    """Send an acknowledgment email to the customer"""
    html_content = f"""
    <h1>We've received your support request</h1>
    <p>Thank you for contacting us. Your support ticket (#{ticket_id}) has been created and our team will respond shortly.</p>
    <p>Please don't reply to this email as it's automatically generated.</p>
    """
    
    if send_email(to_email, f"Support Request Received - Ticket #{ticket_id}", html_content):
        ticket_queue[ticket_id].status = "acknowledged"
        print(f"Sent acknowledgment for ticket #{ticket_id}")

def cleanup():
    """Clean up resources before exiting"""
    global running, email_thread, telegram_loop_thread
    
    print("\nCleaning up resources...")
    running = False
    
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
    register_handlers(bot)
    
    # Reset the running flag
    running = True
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup(), sys.exit(0)))
    
    # Start email checking thread
    email_thread = threading.Thread(target=lambda: check_new_emails(handle_new_email), daemon=True)
    email_thread.start()
    
    # Start Telegram polling loop
    telegram_loop_thread = threading.Thread(target=telegram_polling_loop, daemon=True)
    telegram_loop_thread.start()

if __name__ == "__main__":
    try:
        print("\n" + "="*50)
        print("📧 EMAIL SUPPORT SYSTEM STARTING 📧")
        print("="*50)
        print(f"IMAP Server: {IMAP_SERVER}:{IMAP_PORT}")
        print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"Ollama Host: {OLLAMA_HOST}")
        print(f"Ollama Model: {OLLAMA_MODEL}")
        print("="*50 + "\n")
        
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
    finally:
        sys.exit(0) 