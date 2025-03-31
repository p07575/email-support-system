import telebot
from datetime import datetime
from typing import Dict
from ..models.ticket import ticket_queue
from ..services.telegram_service import safe_telegram_send, sanitize_telegram_markdown
from ..services.ollama_service import process_with_deepseek
from ..services.email_service import send_response_email

def register_handlers(bot: telebot.TeleBot):
    """Register all Telegram command handlers"""
    
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
            bot.send_message(message.chat.id, f"⏳ Processing your response with Ollama model...")
            processed_response = process_with_deepseek(ticket_queue[ticket_id].plain_message, response_text)
            
            customer_email = ticket_queue[ticket_id].from_email
            
            # First, reply to the agent showing what will be sent
            bot.reply_to(message, f"✅ Sending this response to {customer_email}:\n\n{processed_response}")
            
            # Then send to customer
            if send_response_email(customer_email, ticket_id, processed_response):
                ticket_queue[ticket_id].status = "responded"
                ticket_queue[ticket_id].response_time = datetime.now().isoformat()
                ticket_queue[ticket_id].response = processed_response
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
            safe_email = sanitize_telegram_markdown(data.from_email)
            safe_subject = sanitize_telegram_markdown(data.subject)
            
            status_text += f"Ticket: #{ticket_id}\n"
            status_text += f"From: {safe_email}\n"
            status_text += f"Subject: {safe_subject}\n"
            status_text += f"Status: {data.status}\n\n"
            
        safe_telegram_send(message.chat.id, status_text)

    @bot.message_handler(commands=['list'])
    def handle_list(message):
        if not ticket_queue:
            bot.reply_to(message, "No tickets in the queue.")
            return
            
        # Sort tickets by most recent first
        sorted_tickets = sorted(
            ticket_queue.items(),
            key=lambda x: x[1].received_at, 
            reverse=True
        )
        
        list_text = "📋 Recent Tickets:\n\n"
        
        # Show the 10 most recent tickets
        for ticket_id, data in sorted_tickets[:10]:
            received_time = data.received_at
            # Try to format the time to be more readable
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
                
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(data.from_email)
            safe_subject = sanitize_telegram_markdown(data.subject)
            
            list_text += f"#{ticket_id} - {data.status}\n"
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
            received_time = data.received_at
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
            
            # Use plain text version if available
            message_preview = data.plain_message
            message_preview = message_preview[:500] + "..." if len(message_preview) > 500 else message_preview
            
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(data.from_email)
            safe_subject = sanitize_telegram_markdown(data.subject)
            safe_message = sanitize_telegram_markdown(message_preview)
            
            # Format the message text with formatting
            ticket_text = (
                f"🎫 Ticket Details: #{ticket_id}\n\n"
                f"From: {safe_email}\n"
                f"Subject: {safe_subject}\n"
                f"Status: {data.status}\n"
                f"Received: {received_time}\n\n"
                f"Message:\n{safe_message}\n\n"
            )
            
            if data.response:
                # Format response time
                response_time = data.response_time
                try:
                    dt = datetime.fromisoformat(response_time)
                    response_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                    
                safe_response = sanitize_telegram_markdown(data.response[:500] + "...")
                ticket_text += (
                    f"Response:\n"
                    f"{safe_response}\n\n"
                    f"Response Time: {response_time}\n"
                )
                
            # Add reply button/instructions
            ticket_text += f"\nTo reply, use:\n/reply {ticket_id} Your response here"
                
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