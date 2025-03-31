import sys

sys.dont_write_bytecode = True

import os
from dotenv import load_dotenv
import telebot
import ollama
import time
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import threading
from datetime import datetime
import signal
import atexit
import json
import html
import re
import requests

# Load environment variables
load_dotenv()

# Email server settings
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

# Initialize Telegram bot settings
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
support_chat_id = os.getenv("TELEGRAM_SUPPORT_CHAT_ID")

# Configure Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
ollama.host = OLLAMA_HOST

# Global state
running = True
email_thread = None
telegram_loop_thread = None
bot = None  # We'll initialize this later

# Support ticket queue (in-memory for simplicity)
ticket_queue = {}

def sanitize_telegram_markdown(text):
    """
    Very aggressive sanitization for Telegram Markdown formatting to avoid API errors.
    """
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

def safe_telegram_send(chat_id, message, parse_mode=None, retry=True):
    """
    Safely send a message to Telegram, handling potential API errors.
    Always tries plain text first now, for reliability.
    """
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

def test_ollama_connection():
    """Test if the Ollama server is reachable and the model is available"""
    try:
        print(f"Testing connection to Ollama server at {OLLAMA_HOST}...")
        # Try a basic request to get model list
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code != 200:
            print(f"Error connecting to Ollama: HTTP status {response.status_code}")
            return False
            
        models = response.json().get('models', [])
        print(f"Found {len(models)} models on Ollama server")
        
        # Check if our model is available
        model_names = [m.get('name') for m in models]
        if OLLAMA_MODEL not in model_names:
            print(f"Warning: Model '{OLLAMA_MODEL}' not found in available models: {model_names}")
            return False
            
        print(f"Ollama connection test successful - model '{OLLAMA_MODEL}' is available")
        return True
    except Exception as e:
        print(f"Error testing Ollama connection: {e}")
        print(f"Make sure Ollama is running at {OLLAMA_HOST}")
        return False

def html_to_text(html_content):
    """Convert HTML to plain text by removing tags"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Fix spacing
    text = re.sub(r'\s+', ' ', text)
    # Handle special HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    # Trim whitespace
    return text.strip()

def send_email(to_email, subject, html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_email
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Email sent to {to_email}: {subject}")
            return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def print_email_details(email_message, body):
    """Debug function to print out detailed email information"""
    print("\n" + "="*50)
    print("📧 EMAIL DEBUG INFORMATION 📧")
    print("="*50)
    
    print(f"From: {email_message.get('From', 'Unknown')}")
    print(f"To: {email_message.get('To', 'Unknown')}")
    print(f"Subject: {email_message.get('Subject', 'No Subject')}")
    print(f"Date: {email_message.get('Date', 'Unknown')}")
    
    print("\nHeaders:")
    for header, value in email_message.items():
        if header not in ['From', 'To', 'Subject', 'Date']:
            print(f"  {header}: {value}")
    
    print("\nBody Preview (first 300 chars):")
    body_preview = body[:300].replace('\n', ' ')
    print(f"  {body_preview}...")
    
    if '<html' in body.lower() or '<div' in body.lower() or '<p' in body.lower():
        plain_text = html_to_text(body)
        print("\nConverted to Plain Text:")
        print(f"  {plain_text[:300]}...")
    
    print("\nBody Length:", len(body))
    
    print("="*50 + "\n")

def check_new_emails():
    global running
    while running:
        try:
            print("Checking for new emails...")
            with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as imap:
                imap.login(IMAP_USERNAME, IMAP_PASSWORD)
                imap.select('INBOX')
                
                if not running:
                    break
                
                # Search for unread emails
                _, message_numbers = imap.search(None, 'UNSEEN')
                
                num_messages = len(message_numbers[0].split())
                if num_messages > 0:
                    print(f"Found {num_messages} new email(s)")
                else:
                    print("No new emails")
                
                for num in message_numbers[0].split():
                    if not running:
                        break
                    
                    print(f"Processing email #{num}...")
                    _, msg_data = imap.fetch(num, '(RFC822)')
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Extract email details
                    subject = decode_header(email_message["subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    
                    from_email = decode_header(email_message["from"])[0][0]
                    if isinstance(from_email, bytes):
                        from_email = from_email.decode()
                    
                    # Extract email address from the "from_email" field which might include name
                    email_pattern = r'[\w\.-]+@[\w\.-]+'
                    match = re.search(email_pattern, from_email)
                    if match:
                        from_email = match.group(0)
                    
                    # Get email body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            # Skip attachments
                            if "attachment" in content_disposition:
                                continue
                                
                            if content_type == "text/html":
                                body = part.get_payload(decode=True).decode()
                                break
                            elif content_type == "text/plain" and not body:
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = email_message.get_payload(decode=True).decode()
                    
                    # Convert HTML body to plain text if needed
                    plain_body = body
                    if '<html' in body.lower() or '<div' in body.lower() or '<p' in body.lower():
                        plain_body = html_to_text(body)
                    
                    # Print detailed email information for debugging
                    print_email_details(email_message, body)
                    
                    # Generate ticket ID
                    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    print(f"New email received from {from_email}, Subject: {subject}")
                    
                    # Store in queue
                    ticket_queue[ticket_id] = {
                        "from_email": from_email,
                        "subject": subject,
                        "message": body,
                        "plain_message": plain_body,
                        "status": "received",
                        "received_at": datetime.now().isoformat()
                    }
                    
                    # Send acknowledgment
                    send_acknowledgment(from_email, ticket_id)
                    
                    # Forward to Telegram
                    forward_to_telegram(ticket_id, from_email, subject, plain_body)
                    
        except Exception as e:
            print(f"Error checking emails: {str(e)}")
            if not running:
                break
        
        # Sleep with interruption check
        print(f"Waiting 60 seconds before checking again...")
        for _ in range(60):
            if not running:
                break
            time.sleep(1)

def initialize_telegram():
    global bot
    # Create a new bot instance with a specific session name
    bot = telebot.TeleBot(telegram_token, threaded=False)
    
    # Set bot commands for menu display
    bot.set_my_commands([
        telebot.types.BotCommand("/help", "Show available commands"),
        telebot.types.BotCommand("/status", "Show current tickets in the queue"),
        telebot.types.BotCommand("/list", "List recent tickets"),
        telebot.types.BotCommand("/ticket", "Show details of a specific ticket (usage: /ticket ticket_id)"),
        telebot.types.BotCommand("/reply", "Reply to a ticket (usage: /reply ticket_id your_response)")
    ])
    
    # Register the message handler for the /reply command
    @bot.message_handler(commands=['reply'])
    def handle_reply(message):
        try:
            command_parts = message.text.split(' ', 2)
            if len(command_parts) < 3:
                bot.reply_to(message, "❌ Usage: /reply ticket_id your_response")
                return
                
            ticket_id = command_parts[1]
            response_text = command_parts[2]
            
            if ticket_id not in ticket_queue:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found in the queue.")
                return
                
            # Process response with DeepSeek via Ollama before sending
            bot.send_message(message.chat.id, f"⏳ Processing your response with Ollama model {OLLAMA_MODEL} at {OLLAMA_HOST}...")
            processed_response = process_with_deepseek(ticket_id, response_text)
            
            customer_email = ticket_queue[ticket_id]["from_email"]
            
            # First, reply to the agent showing what will be sent
            bot.reply_to(message, f"✅ Sending this response to {customer_email}:\n\n{processed_response}")
            
            # Then send to customer
            if send_response_email(customer_email, ticket_id, processed_response):
                ticket_queue[ticket_id]["status"] = "responded"
                ticket_queue[ticket_id]["response_time"] = datetime.now().isoformat()
                ticket_queue[ticket_id]["response"] = processed_response
                bot.send_message(message.chat.id, f"✅ Response delivered to customer for ticket #{ticket_id}")
            else:
                bot.send_message(message.chat.id, f"❌ Failed to deliver email for ticket #{ticket_id}")
        except Exception as e:
            bot.reply_to(message, f"❌ Error processing reply: {str(e)}")

    @bot.message_handler(commands=['start', 'help'])
    def handle_help(message):
        help_text = (
            "📧 Email Support Bot 📧\n\n"
            "This bot helps you handle customer support emails.\n\n"
            "Commands:\n"
            "/reply ticket_id your_response - Reply to a customer ticket\n"
            "/status - Show current tickets in the queue\n"
            "/list - List all recent tickets\n"
            "/ticket ticket_id - Show details of a specific ticket\n"
            "/help - Show this help message"
        )
        safe_telegram_send(message.chat.id, help_text)

    @bot.message_handler(commands=['status'])
    def handle_status(message):
        if not ticket_queue:
            bot.reply_to(message, "No active tickets in the queue.")
            return
            
        status_text = "📋 Current Tickets:\n\n"
        for ticket_id, data in ticket_queue.items():
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(data['from_email'])
            safe_subject = sanitize_telegram_markdown(data['subject'])
            
            status_text += f"Ticket: #{ticket_id}\n"
            status_text += f"From: {safe_email}\n"
            status_text += f"Subject: {safe_subject}\n"
            status_text += f"Status: {data['status']}\n\n"
            
        safe_telegram_send(message.chat.id, status_text)

    @bot.message_handler(commands=['list'])
    def handle_list(message):
        if not ticket_queue:
            bot.reply_to(message, "No tickets in the queue.")
            return
            
        # Sort tickets by most recent first
        sorted_tickets = sorted(
            ticket_queue.items(),
            key=lambda x: x[1].get('received_at', ''), 
            reverse=True
        )
        
        list_text = "📋 Recent Tickets:\n\n"
        
        # Show the 10 most recent tickets
        for ticket_id, data in sorted_tickets[:10]:
            received_time = data.get('received_at', 'Unknown')
            # Try to format the time to be more readable
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
                
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(data['from_email'])
            safe_subject = sanitize_telegram_markdown(data['subject'])
            
            list_text += f"#{ticket_id} - {data['status']}\n"
            list_text += f"From: {safe_email}\n"
            list_text += f"Subject: {safe_subject}\n"
            list_text += f"Received: {received_time}\n\n"
            
        list_text += "Use /ticket ticketID to view details"
        safe_telegram_send(message.chat.id, list_text)

    @bot.message_handler(commands=['ticket'])
    def handle_ticket(message):
        try:
            command_parts = message.text.split(' ')
            
            # If no ticket ID provided, show usage
            if len(command_parts) < 2:
                bot.reply_to(message, "Usage: /ticket ticket_id\nExample: /ticket TKT-20250329212840")
                return
                
            ticket_id = command_parts[1]
            
            if ticket_id not in ticket_queue:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found in the queue.")
                return
                
            data = ticket_queue[ticket_id]
            
            # Format received time
            received_time = data["received_at"]
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
            
            # Use plain text version if available
            message_preview = data.get("plain_message", data["message"])
            message_preview = message_preview[:500] + "..." if len(message_preview) > 500 else message_preview
            
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(data["from_email"])
            safe_subject = sanitize_telegram_markdown(data["subject"])
            safe_message = sanitize_telegram_markdown(message_preview)
            
            # Format the message text with formatting
            ticket_text = (
                f"🎫 Ticket Details: #{ticket_id}\n\n"
                f"From: {safe_email}\n"
                f"Subject: {safe_subject}\n"
                f"Status: {data['status']}\n"
                f"Received: {received_time}\n\n"
                f"Message:\n{safe_message}\n\n"
            )
            
            if "response" in data and data["response"]:
                # Format response time
                response_time = data.get("response_time", "Unknown")
                try:
                    dt = datetime.fromisoformat(response_time)
                    response_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                    
                safe_response = sanitize_telegram_markdown(data["response"][:500] + "...")
                ticket_text += (
                    f"Response:\n"
                    f"{safe_response}\n\n"
                    f"Response Time: {response_time}\n"
                )
                
            # Add reply command on a separate line for easy copying
            ticket_text += f"\nTo reply, use this command (click to copy):\n/reply {ticket_id}"
                
            safe_telegram_send(message.chat.id, ticket_text)
            
        except Exception as e:
            bot.reply_to(message, f"❌ Error fetching ticket: {str(e)}")
            
    # Handle unknown commands
    @bot.message_handler(func=lambda message: message.text.startswith('/'))
    def handle_unknown_command(message):
        command = message.text.split()[0]
        bot.reply_to(message, f"Unknown command: {command}\nUse /help to see available commands")
        
    # Handle normal messages (not commands)
    @bot.message_handler(func=lambda message: True)
    def handle_direct_message(message):
        bot.reply_to(message, "Please use commands to interact with the bot. Send /help to see available commands.")

def telegram_polling_loop():
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

def forward_to_telegram(ticket_id, from_email, subject, message):
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
    
    # Make the reply command a separate line so it's easily copiable
    telegram_message = (
        f"🆕 New Support Request\n"
        f"Ticket ID: #{ticket_id}\n"
        f"From: {safe_from_email}\n"
        f"Subject: {safe_subject}\n\n"
        f"Message:\n{safe_message_preview}\n\n"
        f"To reply, use this command (click to copy):\n"
        f"/reply {ticket_id}"
    )
    
    try:
        safe_telegram_send(support_chat_id, telegram_message)
        ticket_queue[ticket_id]["status"] = "forwarded_to_support"
        print(f"Forwarded ticket #{ticket_id} to Telegram")
    except Exception as e:
        print(f"Error forwarding to Telegram: {e}")

def send_acknowledgment(to_email, ticket_id):
    html_content = f"""
    <h1>We've received your support request</h1>
    <p>Thank you for contacting us. Your support ticket (#{ticket_id}) has been created and our team will respond shortly.</p>
    <p>Please don't reply to this email as it's automatically generated.</p>
    """
    
    if send_email(to_email, f"Support Request Received - Ticket #{ticket_id}", html_content):
        ticket_queue[ticket_id]["status"] = "acknowledged"
        print(f"Sent acknowledgment for ticket #{ticket_id}")

def process_with_deepseek(ticket_id, response_text):
    print(f"Processing response for ticket #{ticket_id} with Ollama model {OLLAMA_MODEL} via {OLLAMA_HOST}...")
    original_query = ticket_queue[ticket_id].get("plain_message", ticket_queue[ticket_id]["message"])
    
    # Shorten the original query if it's too long
    max_len = 1000
    if len(original_query) > max_len:
        original_query = original_query[:max_len] + "..."
    
    prompt = f"""
    You are a professional customer support agent from StudyFate. Provide a direct, concise, and helpful response.
    
    Original customer query:
    {original_query}
    
    Support agent's response:
    {response_text}
    
    Your task:
    1. Improve the response to be more helpful, professional, and empathetic.
    2. Maintain the key information from the original response.
    3. Ensure the tone is consistent with our brand and the response is clear and concise.
    4. Format any bullet points with proper line breaks.
    5. Provide ONLY the improved response text without any explanations, thoughts, or formatting markers.
    6. DO NOT include any greeting or signature - these will be added automatically.
    7. DO NOT include any <think> sections, meta-commentary, or notes to yourself.
    """
    
    try:
        print(f"Sending request to Ollama at {OLLAMA_HOST} using model {OLLAMA_MODEL}...")
        
        # Check if OLLAMA_MODEL contains a slash - if so, it might not work with ollama.chat
        if '/' in OLLAMA_MODEL:
            # Use direct API call via requests instead
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            if response.status_code != 200:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")
                
            result = response.json()
            improved_response = result.get('response', '')
        else:
            # Use ollama library
            response = ollama.chat(model=OLLAMA_MODEL, messages=[
        {"role": "user", "content": prompt}
    ])
            improved_response = response['message']['content']
        
        # Clean up the response - remove any thinking sections
        improved_response = re.sub(r'<think>.*?</think>', '', improved_response, flags=re.DOTALL)
        
        # Remove common prefixes that models like to add
        prefixes_to_remove = [
            "Here's an improved response:",
            "Here is the improved response:",
            "Improved response:",
            "I would respond with:",
            "I would say:",
            "Response:",
            "---",
            "```"
        ]
        
        for prefix in prefixes_to_remove:
            if improved_response.strip().startswith(prefix):
                improved_response = improved_response.replace(prefix, "", 1).strip()
        
        # Remove any trailing formatting markers
        improved_response = improved_response.replace("---", "").replace("```", "")
        
        # Remove Dear Customer or Thanks from AI output if it added them anyway
        improved_response = re.sub(r'^Dear Customer,?\s*', '', improved_response, flags=re.IGNORECASE)
        improved_response = re.sub(r'Thanks,?\s*The StudyFate Team\s*$', '', improved_response, flags=re.IGNORECASE)
        improved_response = improved_response.strip()
        
        print(f"Response processed successfully by Ollama {OLLAMA_MODEL}")
        
        # Add greeting and signature directly
        formatted_response = f"Dear Customer,\n\n{improved_response}\n\nThanks,\nThe StudyFate Team"
            
        return formatted_response
    except Exception as e:
        print(f"Error processing with Ollama: {e}")
        print("Returning original response without AI processing")
        # If Ollama fails, return the original response with proper greeting and signature
        original_with_format = f"Dear Customer,\n\n{response_text}\n\nThanks,\nThe StudyFate Team"
        return original_with_format

def send_response_email(to_email, ticket_id, response_content):
    # Convert Markdown to HTML for emails
    # Bold: **text** -> <strong>text</strong>
    html_response = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_content)
    
    # Italic: *text* -> <em>text</em> (but don't match ** patterns we already handled)
    html_response = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<em>\1</em>', html_response)
    
    # Convert newlines to HTML breaks for proper formatting
    html_response = html_response.replace('\n', '<br>')
    
    # Convert bullet points for better formatting
    html_response = re.sub(r'- (.*?)(<br>|$)', r'• \1\2', html_response)
    
    html_content = f"""
        <h2>Our Response to Your Support Request</h2>
    <div style="margin-bottom: 20px; line-height: 1.5;">
        {html_response}
    </div>
        <p>If you have any further questions, please feel free to reply to this email.</p>
    <p style="color: #666; font-size: 0.9em;">Ticket ID: #{ticket_id}</p>
    """
    
    return send_email(to_email, f"Re: {ticket_queue[ticket_id]['subject']} - Ticket #{ticket_id}", html_content)

def cleanup():
    global running, email_thread, telegram_loop_thread
    
    print("\nCleaning up resources...")
    running = False
    
    if email_thread and email_thread.is_alive():
        email_thread.join(timeout=5)
        
    if telegram_loop_thread and telegram_loop_thread.is_alive():
        telegram_loop_thread.join(timeout=5)
    
    print("Cleanup complete. Exiting.")

def start_background_tasks():
    global email_thread, telegram_loop_thread, running, bot
    
    # Initialize the bot
    initialize_telegram()
    
    # Reset the running flag
    running = True
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup(), sys.exit(0)))
    
    # Start email checking thread
    email_thread = threading.Thread(target=check_new_emails, daemon=True)
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