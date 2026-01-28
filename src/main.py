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
    DB_HOST, DB_NAME,
    AUTO_REPLY_ENABLED, AUTO_FILTER_ENABLED,
    OPENROUTER_API_KEY, RAG_KNOWLEDGE_DIR
)
from src.models.ticket import Ticket
from src.services.email_service import check_new_emails, send_email
from src.services.ollama_service import test_ollama_connection
from src.services.telegram_service import (
    initialize_telegram, 
    telegram_polling_loop, 
    forward_to_telegram,
    forward_to_telegram_with_draft,
    notify_filtered_email,
    set_running_state
)
from src.services.db_service import (
    initialize_db,
    ensure_db_schema,
    save_ticket,
    update_ticket_status,
    save_draft_response
)
from src.services.openrouter_service import test_openrouter_connection, generate_ai_response
from src.services.email_classifier_service import (
    classify_email,
    is_spam_or_promotion,
    needs_response,
    format_classification_summary,
    EmailCategory
)
from src.services.rag_service import initialize_rag, get_context_for_email
from src.handlers.telegram_handlers import register_handlers

# Global state
running = True
email_thread = None
telegram_loop_thread = None

def handle_new_email(from_email: str, subject: str, body: str, plain_body: str, attachments: List[Dict] = None) -> None:
    """Handle a new email by classifying, creating a ticket, and optionally auto-responding"""
    # Generate ticket ID
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print("\n" + "="*50)
    print(f"HANDLING NEW EMAIL: {subject}")
    print(f"From: {from_email}")
    print(f"Body length: {len(body)} characters")
    
    # === STEP 1: Classify the email ===
    if AUTO_FILTER_ENABLED:
        print("\n📊 Classifying email...")
        classification = classify_email(from_email, subject, plain_body)
        print(format_classification_summary(classification))
        
        # Check if this is spam/promotion - auto-filter
        if is_spam_or_promotion(classification):
            print(f"🗑️ Email classified as {classification.category.value} - filtering out")
            # Notify via Telegram about filtered email (optional)
            notify_filtered_email(from_email, subject, classification)
            print("="*50 + "\n")
            return
        
        # Check if email needs response
        if not needs_response(classification):
            print(f"📁 Email classified as {classification.category.value} - archiving without response")
            # Still save to database for records
            save_ticket(ticket_id, from_email, subject, body, plain_body, attachments)
            update_ticket_status(ticket_id, "archived")
            print("="*50 + "\n")
            return
    
    # === STEP 2: Log attachment info ===
    if attachments and len(attachments) > 0:
        print(f"📎 EMAIL HAS {len(attachments)} ATTACHMENT(S) 📎")
        for i, attachment in enumerate(attachments):
            print(f"  Attachment {i+1}: {attachment['filename']}")
            print(f"  Type: {attachment.get('content_type', 'unknown')}")
            print(f"  Size: {attachment.get('size', 0)} bytes")
    else:
        print("📧 No attachments in email")
    
    # === STEP 3: Save ticket to database ===
    success = save_ticket(ticket_id, from_email, subject, body, plain_body, attachments)
    if not success:
        print(f"Failed to save ticket #{ticket_id} to database")
        return
    
    # === STEP 4: Send acknowledgment ===
    send_acknowledgment(from_email, ticket_id)
    
    # === STEP 5: Generate AI draft response if auto-reply enabled ===
    draft_response = None
    if AUTO_REPLY_ENABLED:
        print("\n🤖 Generating AI draft response...")
        
        # Get RAG context
        context = get_context_for_email(plain_body)
        if context:
            print(f"📚 Found relevant context from knowledge base ({len(context)} chars)")
        else:
            print("📚 No relevant context found in knowledge base")
        
        # Generate response using OpenRouter
        draft_response = generate_ai_response(plain_body, context)
        
        if draft_response:
            print(f"✅ Generated draft response ({len(draft_response)} chars)")
            # Save draft to database
            save_draft_response(ticket_id, draft_response)
        else:
            print("❌ Failed to generate draft response")
    
    # === STEP 6: Forward to Telegram with draft for confirmation ===
    if AUTO_REPLY_ENABLED and draft_response:
        forward_to_telegram_with_draft(ticket_id, from_email, subject, plain_body, draft_response, attachments)
    else:
        forward_to_telegram(ticket_id, from_email, subject, plain_body, attachments)
    
    print("="*50 + "\n")

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
        print(f"Database: MySQL at {DB_HOST}/{DB_NAME}")
        print(f"Auto-Reply: {'✅ Enabled' if AUTO_REPLY_ENABLED else '❌ Disabled'}")
        print(f"Auto-Filter: {'✅ Enabled' if AUTO_FILTER_ENABLED else '❌ Disabled'}")
        print(f"Knowledge Base: {RAG_KNOWLEDGE_DIR}")
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
        
        # Initialize RAG service
        print("Initializing RAG service...")
        initialize_rag()
        
        # Test OpenRouter connection
        if OPENROUTER_API_KEY:
            openrouter_available = test_openrouter_connection()
            if not openrouter_available:
                print("Warning: OpenRouter connection failed - using fallback responses")
        else:
            print("Warning: OpenRouter API key not set - AI features limited")
        
        # Test Ollama connection (fallback)
        ollama_available = test_ollama_connection()
        if not ollama_available:
            print("Note: Ollama not available (OpenRouter will be used instead)")
        
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