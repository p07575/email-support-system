import telebot
import os
from datetime import datetime
from typing import Dict, List
from ..models.ticket import Ticket
from ..services.telegram_service import (
    safe_telegram_send, 
    sanitize_telegram_markdown, 
    send_file_via_telegram,
    get_pending_confirmation,
    clear_pending_confirmation
)
from ..services.ollama_service import process_with_deepseek
from ..services.openrouter_service import generate_ai_response
from ..services.rag_service import get_context_for_email
from ..services.email_service import send_response_email
from ..services.db_service import (
    save_ticket_response, 
    update_ticket_status, 
    get_ticket, 
    get_recent_tickets, 
    get_all_tickets, 
    get_ticket_attachments,
    get_draft_response
)

def register_handlers(bot: telebot.TeleBot):
    """Register all Telegram command handlers"""
    
    @bot.message_handler(commands=['confirm'])
    def handle_confirm(message):
        """Confirm and send the AI-generated draft response"""
        try:
            command_parts = message.text.split(' ', 1)
            if len(command_parts) < 2:
                bot.reply_to(message, "❌ Usage: /confirm ticket_id")
                return
                
            ticket_id = command_parts[1].strip()
            
            # Get the pending draft
            draft_response = get_pending_confirmation(ticket_id)
            
            # If not in memory, try to get from database
            if not draft_response:
                draft_response = get_draft_response(ticket_id)
            
            if not draft_response:
                bot.reply_to(message, f"❌ No pending draft found for ticket #{ticket_id}. Use /reply instead.")
                return
            
            # Get ticket from database
            ticket_data = get_ticket(ticket_id)
            if not ticket_data:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found.")
                return
            
            customer_email = ticket_data["from_email"]
            
            # Format the response with greeting and signature
            formatted_response = f"Dear Customer,\n\n{draft_response}\n\nThanks,\nThe StudyFate Team"
            
            # Send to customer
            bot.send_message(message.chat.id, f"⏳ Sending confirmed response to {customer_email}...")
            
            if send_response_email(customer_email, ticket_id, formatted_response):
                save_ticket_response(ticket_id, formatted_response)
                clear_pending_confirmation(ticket_id)
                bot.send_message(message.chat.id, f"✅ Response sent successfully for ticket #{ticket_id}")
            else:
                bot.send_message(message.chat.id, f"❌ Failed to send email for ticket #{ticket_id}")
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
    
    @bot.message_handler(commands=['edit'])
    def handle_edit(message):
        """Edit the AI draft and send"""
        try:
            command_parts = message.text.split(' ', 2)
            if len(command_parts) < 3:
                bot.reply_to(message, "❌ Usage: /edit ticket_id your_edits_or_instructions")
                return
                
            ticket_id = command_parts[1].strip()
            edit_instructions = command_parts[2]
            
            # Get ticket from database
            ticket_data = get_ticket(ticket_id)
            if not ticket_data:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found.")
                return
            
            # Get the original draft
            draft_response = get_pending_confirmation(ticket_id)
            if not draft_response:
                draft_response = get_draft_response(ticket_id)
            
            customer_email = ticket_data["from_email"]
            
            bot.send_message(message.chat.id, f"⏳ Processing your edits...")
            
            # Get RAG context
            context = get_context_for_email(ticket_data["plain_message"])
            
            # Generate improved response with edit instructions
            improved_response = generate_ai_response(
                customer_query=ticket_data["plain_message"],
                context=context,
                draft_response=f"{draft_response}\n\nUser edits/instructions: {edit_instructions}"
            )
            
            # Format the response
            formatted_response = f"Dear Customer,\n\n{improved_response}\n\nThanks,\nThe StudyFate Team"
            
            # Show the edited response
            bot.send_message(message.chat.id, f"📝 Edited response:\n\n{formatted_response[:1000]}...")
            
            # Send to customer
            if send_response_email(customer_email, ticket_id, formatted_response):
                save_ticket_response(ticket_id, formatted_response)
                clear_pending_confirmation(ticket_id)
                bot.send_message(message.chat.id, f"✅ Edited response sent for ticket #{ticket_id}")
            else:
                bot.send_message(message.chat.id, f"❌ Failed to send email for ticket #{ticket_id}")
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
    
    @bot.message_handler(commands=['regenerate'])
    def handle_regenerate(message):
        """Regenerate AI response for a ticket"""
        try:
            command_parts = message.text.split(' ', 1)
            if len(command_parts) < 2:
                bot.reply_to(message, "❌ Usage: /regenerate ticket_id")
                return
                
            ticket_id = command_parts[1].strip()
            
            # Get ticket from database
            ticket_data = get_ticket(ticket_id)
            if not ticket_data:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found.")
                return
            
            bot.send_message(message.chat.id, f"⏳ Regenerating AI response...")
            
            # Get RAG context
            context = get_context_for_email(ticket_data["plain_message"])
            
            # Generate new response
            new_response = generate_ai_response(
                customer_query=ticket_data["plain_message"],
                context=context
            )
            
            # Store as pending
            from ..services.telegram_service import set_pending_confirmation
            set_pending_confirmation(ticket_id, new_response)
            
            # Show the new response
            safe_response = sanitize_telegram_markdown(new_response[:800])
            bot.send_message(
                message.chat.id, 
                f"🤖 New AI Draft for #{ticket_id}:\n\n{safe_response}\n\n"
                f"/confirm {ticket_id} - Send this\n"
                f"/edit {ticket_id} changes - Edit and send"
            )
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")

    @bot.message_handler(commands=['reply'])
    def handle_reply(message):
        try:
            command_parts = message.text.split(' ', 2)
            if len(command_parts) < 3:
                bot.reply_to(message, "❌ Usage: /reply ticket_id your_response")
                return
                
            ticket_id = command_parts[1]
            response_text = command_parts[2]
            
            # Get ticket from database
            ticket_data = get_ticket(ticket_id)
            if not ticket_data:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found in the database.")
                return
                
            # Process response with DeepSeek via Ollama before sending
            bot.send_message(message.chat.id, f"⏳ Processing your response with Ollama model...")
            processed_response = process_with_deepseek(ticket_data["plain_message"], response_text)
            
            customer_email = ticket_data["from_email"]
            
            # First, reply to the agent showing what will be sent
            bot.reply_to(message, f"✅ Sending this response to {customer_email}:\n\n{processed_response}")
            
            # Check if there are file attachments in this chat (for replies with files)
            # This is a workaround since the original message might not contain file attachments
            # We'll check the last 5 messages in the chat for files
            attachments = []
            try:
                # Get chat history
                updates = bot.get_updates()
                
                # Find files sent by the user before this command
                for update in reversed(updates):
                    # Skip non-message updates
                    if not hasattr(update, 'message') or not update.message:
                        continue
                        
                    # Skip messages not from this user or chat
                    if update.message.chat.id != message.chat.id or update.message.from_user.id != message.from_user.id:
                        continue
                        
                    # Check if message has document
                    if hasattr(update.message, 'document') and update.message.document:
                        file_info = bot.get_file(update.message.document.file_id)
                        file_path = os.path.join(os.path.expanduser('~'), 'temp_attachments', update.message.document.file_name)
                        
                        # Create directory if it doesn't exist
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # Download file
                        downloaded_file = bot.download_file(file_info.file_path)
                        with open(file_path, 'wb') as f:
                            f.write(downloaded_file)
                            
                        attachments.append({
                            'filename': update.message.document.file_name,
                            'path': file_path,
                            'content_type': update.message.document.mime_type,
                            'size': update.message.document.file_size
                        })
                
                if attachments:
                    bot.send_message(message.chat.id, f"🔖 Including {len(attachments)} attachment(s) with your response")
            except Exception as e:
                print(f"Error processing attachments: {e}")
                # Continue without attachments if there's an error
                attachments = []
            
            # Then send to customer
            if send_response_email(customer_email, ticket_id, processed_response, attachments):
                # Update ticket in database
                save_ticket_response(ticket_id, processed_response)
                bot.send_message(message.chat.id, f"✅ Response delivered to customer for ticket #{ticket_id}")
            else:
                bot.send_message(message.chat.id, f"❌ Failed to deliver email for ticket #{ticket_id}")
        except Exception as e:
            bot.reply_to(message, f"❌ Error processing reply: {str(e)}")

    @bot.message_handler(commands=['start', 'help'])
    def handle_help(message):
        help_text = (
            "📧 Email Support Bot 📧\n\n"
            "This bot helps you handle customer support emails with AI assistance.\n\n"
            "🤖 AI Auto-Reply Commands:\n"
            "/confirm ticket_id - Send the AI-generated draft\n"
            "/edit ticket_id changes - Edit draft and send\n"
            "/regenerate ticket_id - Generate a new AI response\n\n"
            "📝 Manual Commands:\n"
            "/reply ticket_id your_response - Write custom response\n"
            "/status - Show active tickets\n"
            "/list - List recent tickets\n"
            "/ticket ticket_id - Show ticket details\n"
            "/help - Show this help message\n\n"
            "📚 Knowledge Base:\n"
            "/kb list - List knowledge base documents\n"
            "/kb add - Instructions to add documents\n\n"
            "ℹ️ AI drafts are generated automatically when new emails arrive."
        )
        safe_telegram_send(message.chat.id, help_text)

    @bot.message_handler(commands=['status'])
    def handle_status(message):
        # Get all tickets from database
        tickets = get_all_tickets()
        
        # Filter out tickets with status 'responded'
        active_tickets = [ticket for ticket in tickets if ticket['status'] != 'responded']
        
        if not active_tickets:
            bot.reply_to(message, "No active tickets in the queue.")
            return
            
        status_text = "📋 Current Tickets:\n\n"
        for ticket in active_tickets:
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(ticket["from_email"])
            safe_subject = sanitize_telegram_markdown(ticket["subject"])
            
            status_text += f"Ticket: #{ticket['id']}\n"
            status_text += f"From: {safe_email}\n"
            status_text += f"Subject: {safe_subject}\n"
            status_text += f"Status: {ticket['status']}\n"
            
            # Show attachment count if any
            if 'attachments' in ticket and ticket['attachments']:
                status_text += f"📎 Attachments: {len(ticket['attachments'])}\n"
                
            status_text += "\n"
            
        safe_telegram_send(message.chat.id, status_text)

    @bot.message_handler(commands=['list'])
    def handle_list(message):
        # Get recent tickets from database
        tickets = get_recent_tickets(10)  # Get 10 most recent tickets
        
        if not tickets:
            bot.reply_to(message, "No tickets in the queue.")
            return
            
        list_text = "📋 Recent Tickets:\n\n"
        
        # Show the tickets
        for ticket in tickets:
            # Format received time
            received_time = ticket["received_at"]
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
                
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(ticket["from_email"])
            safe_subject = sanitize_telegram_markdown(ticket["subject"])
            
            list_text += f"#{ticket['id']} - {ticket['status']}\n"
            list_text += f"From: {safe_email}\n"
            list_text += f"Subject: {safe_subject}\n"
            list_text += f"Received: {received_time}\n"
            
            # Add response time if ticket has been responded to
            if "response" in ticket and ticket["response"] and "response_time" in ticket:
                try:
                    dt = datetime.fromisoformat(ticket["response_time"])
                    response_time = dt.strftime("%Y-%m-%d %H:%M")
                    list_text += f"Responded: {response_time}\n"
                except:
                    pass
                    
            # Show attachment count if any
            if 'attachments' in ticket and ticket['attachments']:
                list_text += f"📎 Attachments: {len(ticket['attachments'])}\n"
            
            list_text += "\n"
            
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
            
            # Get ticket from database
            ticket = get_ticket(ticket_id)
            if not ticket:
                bot.reply_to(message, f"❌ Ticket #{ticket_id} not found in the database.")
                return
                
            # Format received time
            received_time = ticket["received_at"]
            try:
                dt = datetime.fromisoformat(received_time)
                received_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
            
            # Use plain text version if available
            message_preview = ticket["plain_message"]
            message_preview = message_preview[:500] + "..." if len(message_preview) > 500 else message_preview
            
            # Sanitize all fields for Telegram
            safe_email = sanitize_telegram_markdown(ticket["from_email"])
            safe_subject = sanitize_telegram_markdown(ticket["subject"])
            safe_message = sanitize_telegram_markdown(message_preview)
            
            # Format the message text with formatting
            ticket_text = (
                f"🎫 Ticket Details: #{ticket_id}\n\n"
                f"From: {safe_email}\n"
                f"Subject: {safe_subject}\n"
                f"Status: {ticket['status']}\n"
                f"Received: {received_time}"
            )
            
            # Add attachment information if any
            if 'attachments' in ticket and ticket['attachments']:
                attachments = ticket['attachments']
                ticket_text += f"\n\n📎 Attachments ({len(attachments)}):"
                for attachment in attachments:
                    ticket_text += f"\n- {attachment['filename']}"
            
            # Add message preview
            ticket_text += f"\n\nMessage:\n{safe_message}"
            
            # Add response if available
            if "response" in ticket and ticket["response"]:
                # Format response time
                response_time = ticket.get("response_time", "Unknown")
                try:
                    dt = datetime.fromisoformat(response_time)
                    response_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
                    
                safe_response = sanitize_telegram_markdown(ticket["response"][:500] + "..." if len(ticket["response"]) > 500 else ticket["response"])
                ticket_text += (
                    f"\n\nResponse:\n"
                    f"{safe_response}\n\n"
                    f"Response Time: {response_time}"
                )
                
            # Add reply command on a separate line for easy copying
            ticket_text += f"\n\nTo reply, use this command (click to copy):\n/reply {ticket_id}"
                
            # Send ticket information
            safe_telegram_send(message.chat.id, ticket_text)
            
            # Send attachments if any
            if 'attachments' in ticket and ticket['attachments']:
                for attachment in ticket['attachments']:
                    file_path = attachment.get('file_path')
                    if file_path and os.path.exists(file_path):
                        send_file_via_telegram(message.chat.id, file_path, f"Attachment: {attachment['filename']}")
            
        except Exception as e:
            bot.reply_to(message, f"❌ Error fetching ticket: {str(e)}")
    
    @bot.message_handler(commands=['kb'])
    def handle_knowledge_base(message):
        """Handle knowledge base commands"""
        try:
            from ..services.rag_service import get_rag_service
            
            command_parts = message.text.split(' ', 1)
            sub_command = command_parts[1].strip() if len(command_parts) > 1 else "list"
            
            rag = get_rag_service()
            
            if sub_command == "list":
                documents = rag.list_documents()
                if documents:
                    doc_list = "\n".join([f"📄 {doc}" for doc in documents])
                    bot.reply_to(message, f"📚 Knowledge Base Documents:\n\n{doc_list}")
                else:
                    bot.reply_to(message, "📚 No documents in knowledge base yet.\nUse /kb add for instructions.")
                    
            elif sub_command == "add":
                kb_path = rag.knowledge_dir
                bot.reply_to(
                    message,
                    f"📚 Adding Documents to Knowledge Base\n\n"
                    f"Place your documents in:\n{kb_path}\n\n"
                    f"Supported formats:\n"
                    f"- .txt (Plain text)\n"
                    f"- .md (Markdown)\n"
                    f"- .json (JSON data)\n\n"
                    f"The system will automatically load them on restart."
                )
                
            elif sub_command == "reload":
                count = rag.load_documents()
                bot.reply_to(message, f"✅ Reloaded {count} documents from knowledge base.")
                
            else:
                bot.reply_to(message, "Usage:\n/kb list - List documents\n/kb add - How to add documents\n/kb reload - Reload documents")
                
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
            
    # Handle document uploads (for attachments)
    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        bot.reply_to(
            message, 
            "📎 File received. To include this file in your response, use the /reply command after sending the file.\n"
            "For example: /reply TKT-20250401001 Here is the information you requested."
        )
            
    # Handle unknown commands
    @bot.message_handler(func=lambda message: message.text.startswith('/'))
    def handle_unknown_command(message):
        command = message.text.split()[0]
        bot.reply_to(message, f"Unknown command: {command}\nUse /help to see available commands")
        
    # Handle normal messages (not commands)
    @bot.message_handler(func=lambda message: True)
    def handle_direct_message(message):
        bot.reply_to(message, "Please use commands to interact with the bot. Send /help to see available commands.") 