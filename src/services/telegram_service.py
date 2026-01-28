import telebot
import re
import time
import os
from typing import Optional, List, Dict
from ..config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ..services.db_service import update_ticket_status

# Initialize bot
bot = None
running = True  # Default value

# Store pending confirmations: {ticket_id: draft_response}
pending_confirmations: Dict[str, str] = {}


def get_pending_confirmation(ticket_id: str) -> Optional[str]:
    """Get pending draft response for a ticket"""
    return pending_confirmations.get(ticket_id)


def set_pending_confirmation(ticket_id: str, draft: str):
    """Set pending draft response for a ticket"""
    pending_confirmations[ticket_id] = draft


def clear_pending_confirmation(ticket_id: str):
    """Clear pending confirmation for a ticket"""
    if ticket_id in pending_confirmations:
        del pending_confirmations[ticket_id]

def initialize_telegram():
    """Initialize the Telegram bot"""
    global bot
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
    
    # Set bot commands for menu display
    bot.set_my_commands([
        telebot.types.BotCommand("/help", "Show available commands"),
        telebot.types.BotCommand("/status", "Show current tickets in the queue"),
        telebot.types.BotCommand("/list", "List recent tickets"),
        telebot.types.BotCommand("/ticket", "Show details of a specific ticket (usage: /ticket ticket_id)"),
        telebot.types.BotCommand("/reply", "Reply to a ticket (usage: /reply ticket_id your_response)")
    ])
    
    return bot

def sanitize_telegram_markdown(text: str) -> str:
    """Very aggressive sanitization for Telegram Markdown formatting to avoid API errors."""
    if not text:
        return ""
        
    # Convert to string and make a copy for safety
    text = str(text)
    
    # Replace DOT with . in case it's already been converted somewhere
    text = text.replace("DOT", ".")
    
    # Now remove other special characters except email addresses
    # We'll specially handle emails by preserving them exactly as they are
    
    # First extract and protect all email addresses with unique placeholders
    cleaned_text = ""
    i = 0
    while i < len(text):
        # Check if this might be the start of an email
        if i < len(text) - 5 and '@' in text[i:i+20]:
            # Look for email ending (space, newline, or end of string)
            j = i
            while j < len(text) and text[j] not in [' ', '\n', '\r']:
                j += 1
            
            potential_email = text[i:j]
            # Simple email validation
            if '@' in potential_email and '.' in potential_email.split('@')[1]:
                # This looks like an email, preserve it entirely
                cleaned_text += potential_email
                i = j
                continue
        
        # Not an email, process char by char
        if text[i] not in '*_`~>#+=|{}[]\n\r':
            cleaned_text += text[i]
        elif text[i] in ['\n', '\r']:
            cleaned_text += text[i]  # Preserve newlines
        i += 1
    
    # Replace any non-ASCII characters that might cause issues
    cleaned_text = ''.join(c for c in cleaned_text if ord(c) < 128)
    
    # Ensure no more than 2 consecutive newlines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    # Remove excessive spaces
    cleaned_text = re.sub(r'\s{3,}', '  ', cleaned_text)
    
    # Limit text length
    max_length = 2000  # Conservative limit
    if len(cleaned_text) > max_length:
        cleaned_text = cleaned_text[:max_length] + "..."
        
    return cleaned_text

def safe_telegram_send(chat_id: int, message: str, parse_mode: Optional[str] = None, retry: bool = True) -> Optional[telebot.types.Message]:
    """Safely send a message to Telegram, handling potential API errors."""
    global bot
    
    if not bot:
        initialize_telegram()
    
    try:
        # First attempt: Use plain text, no markdown
        return bot.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        
        if retry:
            try:
                # Strip everything down to basic ASCII
                ultra_safe_text = ''.join(c for c in message if 32 <= ord(c) <= 126)
                ultra_safe_text = ultra_safe_text[:1000]  # Very short message
                return bot.send_message(chat_id, ultra_safe_text)
            except Exception as e2:
                print(f"Error sending ultra-safe message: {e2}")
                
                try:
                    return bot.send_message(
                        chat_id, 
                        "⚠️ Message could not be displayed. Please check system logs."
                    )
                except:
                    pass
                    
        return None

def send_file_via_telegram(chat_id: int, file_path: str, caption: Optional[str] = None) -> bool:
    """Send a file to Telegram"""
    global bot
    
    if not bot:
        initialize_telegram()
    
    try:
        print(f"Sending file to Telegram: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ Error: File not found: {file_path}")
            return False
            
        # Get file size
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
        
        # Check if file is too large for Telegram (max 50MB)
        if file_size > 50 * 1024 * 1024:
            print(f"❌ Error: File too large for Telegram: {file_path} ({file_size} bytes)")
            safe_telegram_send(chat_id, f"⚠️ File is too large to send via Telegram: {os.path.basename(file_path)} ({file_size} bytes)")
            return False
        
        # Send file
        print(f"Opening file for sending: {file_path}")
        with open(file_path, 'rb') as f:
            print(f"Calling Telegram API to send document...")
            message = bot.send_document(chat_id, f, caption=caption)
            print(f"Telegram API message_id: {message.message_id}")
        
        print(f"✅ File successfully sent via Telegram: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error sending file via Telegram: {e}")
        # Print the traceback for more detailed error info
        import traceback
        traceback.print_exc()
        return False

def forward_to_telegram(ticket_id: str, from_email: str, subject: str, message: str, attachments: List[Dict] = None) -> None:
    """Forward a new ticket to Telegram"""
    global bot
    
    # Ensure the bot is initialized
    if bot is None:
        initialize_telegram()
    
    # Create a shortened message preview (first 200 chars)
    message_preview = message[:200] + "..." if len(message) > 200 else message
    
    # Sanitize all text fields for Telegram
    safe_from_email = sanitize_telegram_markdown(from_email)
    safe_subject = sanitize_telegram_markdown(subject)
    safe_message_preview = sanitize_telegram_markdown(message_preview)
    
    print(f"Forwarding ticket #{ticket_id} to Telegram")
    
    # Add attachment info if any
    attachment_info = ""
    if attachments and len(attachments) > 0:
        print(f"Including information about {len(attachments)} attachment(s) in Telegram message")
        attachment_info = f"\n📎 Attachments: {len(attachments)}\n"
        for i, attachment in enumerate(attachments):
            attachment_name = attachment.get('filename', 'Unknown')
            attachment_type = attachment.get('content_type', 'unknown')
            attachment_info += f"- {attachment_name} ({attachment_type})\n"
            print(f"  Attachment {i+1}: {attachment_name} ({attachment_type})")
    else:
        print("No attachments to include in Telegram message")
    
    # Make the reply command a separate line so it's easily copiable
    telegram_message = (
        f"🆕 New Support Request\n"
        f"Ticket ID: #{ticket_id}\n"
        f"From: {safe_from_email}\n"
        f"Subject: {safe_subject}\n\n"
        f"Message:\n{safe_message_preview}\n"
        f"{attachment_info}\n"
        f"To reply, use this command (click to copy):\n"
        f"/reply {ticket_id}"
    )
    
    try:
        print(f"Sending ticket #{ticket_id} information to Telegram")
        safe_telegram_send(TELEGRAM_CHAT_ID, telegram_message)
        update_ticket_status(ticket_id, "forwarded_to_support")
        print(f"✅ Forwarded ticket #{ticket_id} information to Telegram")
        
        # Send attachments if any
        if attachments and len(attachments) > 0:
            print(f"Sending {len(attachments)} attachment(s) to Telegram")
            for i, attachment in enumerate(attachments):
                file_path = attachment.get('path')
                if file_path and os.path.exists(file_path):
                    print(f"Sending attachment {i+1}/{len(attachments)}: {attachment['filename']}")
                    caption = f"#{ticket_id} - {attachment['filename']}"
                    success = send_file_via_telegram(TELEGRAM_CHAT_ID, file_path, caption)
                    if success:
                        print(f"✅ Attachment {i+1} sent successfully: {attachment['filename']}")
                    else:
                        print(f"❌ Failed to send attachment {i+1}: {attachment['filename']}")
                else:
                    print(f"❌ Attachment file not found: {file_path}")
            print(f"Finished sending attachments for ticket #{ticket_id}")
        else:
            print(f"No attachments to send for ticket #{ticket_id}")
    except Exception as e:
        print(f"❌ Error forwarding to Telegram: {e}")
        # Print traceback for more detailed error information
        import traceback
        traceback.print_exc()


def forward_to_telegram_with_draft(ticket_id: str, from_email: str, subject: str, message: str, draft_response: str, attachments: List[Dict] = None) -> None:
    """Forward a new ticket to Telegram with AI-generated draft response for confirmation"""
    global bot
    
    # Ensure the bot is initialized
    if bot is None:
        initialize_telegram()
    
    # Store the draft for later confirmation
    set_pending_confirmation(ticket_id, draft_response)
    
    # Create a shortened message preview (first 200 chars)
    message_preview = message[:200] + "..." if len(message) > 200 else message
    
    # Sanitize all text fields for Telegram
    safe_from_email = sanitize_telegram_markdown(from_email)
    safe_subject = sanitize_telegram_markdown(subject)
    safe_message_preview = sanitize_telegram_markdown(message_preview)
    safe_draft = sanitize_telegram_markdown(draft_response[:500] + "..." if len(draft_response) > 500 else draft_response)
    
    print(f"Forwarding ticket #{ticket_id} to Telegram with draft response")
    
    # Add attachment info if any
    attachment_info = ""
    if attachments and len(attachments) > 0:
        attachment_info = f"\n📎 Attachments: {len(attachments)}\n"
        for attachment in attachments:
            attachment_name = attachment.get('filename', 'Unknown')
            attachment_info += f"- {attachment_name}\n"
    
    # Message with draft and confirmation options
    telegram_message = (
        f"🆕 New Support Request (AI Draft Ready)\n"
        f"Ticket ID: #{ticket_id}\n"
        f"From: {safe_from_email}\n"
        f"Subject: {safe_subject}\n\n"
        f"📩 Customer Message:\n{safe_message_preview}\n"
        f"{attachment_info}\n"
        f"🤖 AI Draft Response:\n{safe_draft}\n\n"
        f"Actions:\n"
        f"/confirm {ticket_id} - Send this draft response\n"
        f"/edit {ticket_id} your_changes - Edit and send\n"
        f"/reply {ticket_id} custom_response - Write your own response"
    )
    
    try:
        safe_telegram_send(TELEGRAM_CHAT_ID, telegram_message)
        update_ticket_status(ticket_id, "pending_confirmation")
        print(f"✅ Forwarded ticket #{ticket_id} with draft to Telegram")
        
        # Send attachments if any
        if attachments and len(attachments) > 0:
            for attachment in attachments:
                file_path = attachment.get('path')
                if file_path and os.path.exists(file_path):
                    caption = f"#{ticket_id} - {attachment['filename']}"
                    send_file_via_telegram(TELEGRAM_CHAT_ID, file_path, caption)
    except Exception as e:
        print(f"❌ Error forwarding to Telegram: {e}")
        import traceback
        traceback.print_exc()


def notify_filtered_email(from_email: str, subject: str, classification) -> None:
    """Notify about a filtered (spam/promotion) email"""
    global bot
    
    # Ensure the bot is initialized
    if bot is None:
        initialize_telegram()
    
    safe_from_email = sanitize_telegram_markdown(from_email)
    safe_subject = sanitize_telegram_markdown(subject[:100])
    
    message = (
        f"🗑️ Email Filtered\n"
        f"From: {safe_from_email}\n"
        f"Subject: {safe_subject}\n"
        f"Category: {classification.category.value}\n"
        f"Confidence: {classification.confidence:.0%}\n"
        f"Reason: {classification.reason}"
    )
    
    try:
        safe_telegram_send(TELEGRAM_CHAT_ID, message)
    except Exception as e:
        print(f"Error notifying about filtered email: {e}")

def telegram_polling_loop():
    """Main Telegram polling loop"""
    global bot, running
    
    # First, make sure any existing webhook is removed
    try:
        bot.remove_webhook()
        time.sleep(0.5)  # Short delay
    except Exception as e:
        print(f"Error removing webhook: {e}")
    
    print("Starting Telegram polling loop...")
    
    # Main polling loop
    while running:
        try:
            # Get updates with a short timeout
            updates = bot.get_updates(offset=0, timeout=2)
            
            # Process each update
            if updates:
                for update in updates:
                    try:
                        bot.process_new_updates([update])
                        # Update the offset to acknowledge this update
                        offset = update.update_id + 1
                        bot.get_updates(offset=offset)
                    except Exception as e:
                        print(f"Error processing update: {e}")
            
            # Short sleep to prevent CPU overuse
            time.sleep(1)
            
        except Exception as e:
            print(f"Error in Telegram polling loop: {e}")
            # If there's an error, wait a bit before retrying
            time.sleep(5)
            
            # Try to reset the bot
            try:
                bot.remove_webhook()
            except:
                pass 

def set_running_state(state: bool):
    """Set the running state for the Telegram polling loop"""
    global running
    running = state 