import smtplib
import imaplib
import email
import os
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
import re
from typing import Optional, Tuple, List, Dict
from ..config.settings import (
    EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_USERNAME, EMAIL_PASSWORD,
    EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT, EMAIL_CHECK_INTERVAL
)
import time

def html_to_text(html_content: str) -> str:
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

def send_email(to_email: str, subject: str, html_content: str, attachments: List[Dict] = None) -> bool:
    """Send an email using SMTP with optional attachments"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USERNAME
    msg['To'] = to_email
    
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    
    # Add attachments if any
    if attachments:
        for attachment in attachments:
            # Check if we have binary content or a file path
            if 'content' in attachment:
                part = MIMEApplication(attachment['content'])
                part.add_header('Content-Disposition', 'attachment', 
                               filename=attachment['filename'])
            elif 'path' in attachment:
                with open(attachment['path'], 'rb') as file:
                    part = MIMEApplication(file.read())
                    part.add_header('Content-Disposition', 'attachment', 
                                   filename=os.path.basename(attachment['path']))
            
            msg.attach(part)
    
    try:
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"Email sent to {to_email}: {subject}")
            return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def decode_email_header(header_value: str) -> str:
    """Properly decode email headers that may include encoded words or international characters"""
    if not header_value:
        return ""
        
    try:
        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except (UnicodeDecodeError, LookupError):
                        # Fallback encodings if the specified one fails
                        for fallback_encoding in ['utf-8', 'latin1', 'cp1252', 'gb2312', 'big5']:
                            try:
                                decoded_parts.append(part.decode(fallback_encoding))
                                print(f"Used fallback encoding {fallback_encoding} for header")
                                break
                            except (UnicodeDecodeError, LookupError):
                                continue
                        else:
                            # If all fallbacks fail, use repr as last resort
                            decoded_parts.append(repr(part))
                else:
                    # Try utf-8 first, then fallbacks
                    try:
                        decoded_parts.append(part.decode('utf-8'))
                    except UnicodeDecodeError:
                        for fallback_encoding in ['latin1', 'cp1252', 'gb2312', 'big5']:
                            try:
                                decoded_parts.append(part.decode(fallback_encoding))
                                print(f"Used fallback encoding {fallback_encoding} for header")
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # If all fallbacks fail, use repr as last resort
                            decoded_parts.append(repr(part))
            else:
                decoded_parts.append(part)
                
        return ''.join(str(p) for p in decoded_parts)
    except Exception as e:
        print(f"Error decoding header '{header_value}': {e}")
        return header_value  # Return original if decoding fails

def extract_email_details(email_message: email.message.Message) -> Tuple[str, str, str, List[Dict]]:
    """Extract email details and attachments from an email message"""
    # Extract subject with better decoding
    raw_subject = email_message.get("subject", "")
    subject = decode_email_header(raw_subject)
    print(f"Raw subject: {raw_subject}")
    print(f"Decoded subject: {subject}")
    
    # Extract from email with better decoding
    raw_from = email_message.get("from", "")
    from_email_full = decode_email_header(raw_from)
    print(f"Raw from: {raw_from}")
    print(f"Decoded from: {from_email_full}")
    
    # Extract email address from the "from_email" field which might include name
    email_pattern = r'[\w\.-]+@[\w\.-]+'
    match = re.search(email_pattern, from_email_full)
    if match:
        from_email = match.group(0)
    else:
        from_email = from_email_full  # Fallback
    
    # Get email body and attachments
    body = ""
    attachments = []
    
    print(f"Processing email: '{subject}' from '{from_email}'")
    print(f"Email is multipart: {email_message.is_multipart()}")
    
    # Print all email headers for debugging
    print("===== EMAIL HEADERS =====")
    for header, value in email_message.items():
        print(f"{header}: {value}")
    print("=========================")
    
    if email_message.is_multipart():
        for part_index, part in enumerate(email_message.walk()):
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            print(f"Part {part_index}: type={content_type}, disposition={content_disposition}")
            
            # Debug headers for each part
            print(f"Part {part_index} headers:")
            for header, value in part.items():
                print(f"  {header}: {value}")
            
            # Enhanced attachment detection logic
            is_attachment = False
            
            # Check standard Content-Disposition header
            if "attachment" in content_disposition or "inline" in content_disposition:
                is_attachment = True
                print(f"Part {part_index} identified as attachment via Content-Disposition: {content_disposition}")
            
            # Check filename parameters 
            filename = part.get_filename()
            if filename:
                is_attachment = True
                print(f"Part {part_index} has filename: {filename}")
            
            # Check Content-Type name parameter
            content_type_params = part.get_params() or []
            for param in content_type_params:
                if param[0].lower() == 'name':
                    filename = param[1]
                    is_attachment = True
                    print(f"Part {part_index} has Content-Type name param: {filename}")
            
            if is_attachment:
                if not filename:
                    filename = f"attachment_{len(attachments)}"
                
                print(f"Processing attachment: {filename}")
                
                # Get the attachment data
                payload = part.get_payload(decode=True)
                if payload:
                    payload_size = len(payload)
                    print(f"Found attachment: '{filename}', type: {content_type}, size: {payload_size} bytes")
                
                    # Create temporary file to store attachment
                    temp_dir = tempfile.gettempdir()
                    file_path = os.path.join(temp_dir, filename)
                    
                    # Save attachment to temporary file
                    with open(file_path, 'wb') as f:
                        f.write(payload)
                    
                    print(f"Saved attachment to: {file_path}")
                    
                    attachments.append({
                        'filename': filename,
                        'path': file_path,
                        'content_type': content_type,
                        'size': payload_size
                    })
                else:
                    print(f"Warning: Attachment '{filename}' has no payload")
                continue
                
            if content_type == "text/html":
                body = part.get_payload(decode=True).decode()
                print(f"Found HTML body: {len(body)} characters")
                break
            elif content_type == "text/plain" and not body:
                body = part.get_payload(decode=True).decode()
                print(f"Found plain text body: {len(body)} characters")
    else:
        body = email_message.get_payload(decode=True).decode()
        print(f"Non-multipart email, body length: {len(body)} characters")
    
    print(f"Extracted {len(attachments)} attachments from email")
    return from_email, subject, body, attachments

def check_new_emails(callback) -> None:
    """Check for new emails in a continuous loop and call the callback function for each new email"""
    # Use the global running variable from main module
    import src.main
    
    while src.main.running:
        try:
            print("Checking for new emails...")
            print(f"Connecting to IMAP server: {EMAIL_IMAP_SERVER}:{EMAIL_IMAP_PORT}")
            
            with imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT) as imap:
                print("IMAP connection established")
                imap.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                print(f"Logged in as {EMAIL_USERNAME}")
                imap.select('INBOX')
                print("Selected INBOX folder")
                
                # Check if we're still running
                if not src.main.running:
                    break
                
                # Search for unread emails
                print("Searching for unread emails...")
                status, message_numbers = imap.search(None, 'UNSEEN')
                print(f"Search status: {status}")
                
                num_messages = len(message_numbers[0].split())
                if num_messages > 0:
                    print(f"Found {num_messages} new email(s)")
                else:
                    print("No new emails")
                
                for num in message_numbers[0].split():
                    # Check if we're still running
                    if not src.main.running:
                        break
                        
                    print(f"Processing email #{num}...")
                    status, msg_data = imap.fetch(num, '(RFC822)')
                    if status != 'OK':
                        print(f"Error fetching email #{num}: {status}")
                        continue
                    
                    print(f"Successfully fetched email #{num}")
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Extract email details
                    print(f"Extracting details from email #{num}...")
                    from_email, subject, body, attachments = extract_email_details(email_message)
                    
                    # If no attachments were found using regular method, try alternative method
                    if not attachments and email_message.is_multipart():
                        print("No attachments found with standard extraction, trying fallback method...")
                        fallback_attachments = extract_attachments_fallback(email_message)
                        if fallback_attachments:
                            print(f"Fallback method found {len(fallback_attachments)} attachment(s)")
                            attachments = fallback_attachments
                    
                    # Convert HTML body to plain text if needed
                    plain_body = body
                    if '<html' in body.lower() or '<div' in body.lower() or '<p' in body.lower():
                        plain_body = html_to_text(body)
                        print(f"Converted HTML to plain text: {len(plain_body)} characters")
                    
                    # Call the callback function with the email details
                    print(f"Calling callback for email #{num} with {len(attachments)} attachment(s)")
                    callback(from_email, subject, body, plain_body, attachments)
                
            # Wait before checking again (using EMAIL_CHECK_INTERVAL env var)
            interval = EMAIL_CHECK_INTERVAL
            print(f"Waiting {interval} seconds before checking again...")
            for _ in range(interval):
                if not src.main.running:
                    break
                time.sleep(1)
                
        except Exception as e:
            print(f"Error checking emails: {str(e)}")
            # Print the traceback for more detailed error information
            import traceback
            traceback.print_exc()
            
            # Wait a bit longer if there was an error
            print("Waiting 60 seconds after error...")
            for _ in range(60):
                if not src.main.running:
                    break
                time.sleep(1)

def send_response_email(to_email: str, ticket_id: str, response_text: str, attachments: List[Dict] = None) -> bool:
    """Send a response email to a customer with optional attachments"""
    html_content = f"""
    <h2>Response to your support request</h2>
    <p>This is a response to your support ticket (#{ticket_id}).</p>
    <div style="white-space: pre-wrap;">{response_text}</div>
    """
    
    if attachments and len(attachments) > 0:
        html_content += f"<p>We've included {len(attachments)} attachment(s) with this response.</p>"
    
    return send_email(to_email, f"Re: Support Ticket #{ticket_id}", html_content, attachments)

def extract_attachments_fallback(email_message: email.message.Message) -> List[Dict]:
    """Alternative method to extract attachments from email for cases where standard method fails"""
    attachments = []
    
    print("Using fallback attachment extraction method")
    
    # Attachment names sometimes seen in emails
    attachment_types = [
        'application/octet-stream',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument',
        'application/vnd.ms-excel',
        'application/zip',
        'application/x-zip',
        'application/x-zip-compressed',
        'image/png',
        'image/jpeg',
        'image/jpg',
        'image/gif',
        'text/plain',
        'text/csv',
        'text/markdown'
    ]
    
    # Process all parts
    for part in email_message.walk():
        # Skip multipart/* - these are just containers
        if part.get_content_maintype() == 'multipart':
            print(f"Skipping multipart container: {part.get_content_type()}")
            continue
        
        # Skip if it looks like the main message body
        if part.get_content_maintype() == 'text' and part.get_content_disposition() is None:
            if 'attachment' not in str(part.get('Content-Type', '')).lower():
                print(f"Skipping text body: {part.get_content_type()}")
                continue
        
        # Get different possible filenames
        filename = None
        
        # Try Content-Disposition first
        content_disp = part.get('Content-Disposition', '')
        if content_disp:
            print(f"Content-Disposition: {content_disp}")
            
            disp_params = {}
            for item in content_disp.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1)
                    # Strip quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    disp_params[name.lower()] = value
            
            if 'filename' in disp_params:
                filename = disp_params['filename']
                print(f"Found filename in Content-Disposition params: {filename}")
        
        # Try Content-Type name parameter if still no filename
        if not filename:
            content_type = part.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            type_params = {}
            for item in content_type.split(';'):
                item = item.strip()
                if '=' in item:
                    name, value = item.split('=', 1) 
                    # Strip quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    type_params[name.lower()] = value
            
            if 'name' in type_params:
                filename = type_params['name']
                print(f"Found filename in Content-Type params: {filename}")
        
        # Try standard get_filename method as last resort
        if not filename:
            filename = part.get_filename()
            if filename:
                print(f"Found filename with get_filename(): {filename}")
        
        # Try to guess from content type if still no filename
        if not filename:
            # Check if it looks like an attachment by content type
            content_type = part.get_content_type()
            is_likely_attachment = False
            
            # Check against common attachment types
            for att_type in attachment_types:
                if att_type in content_type:
                    is_likely_attachment = True
                    break
            
            if is_likely_attachment:
                # Make a filename based on content type
                ext = content_type.split('/')[-1].replace('jpeg', 'jpg')
                filename = f"attachment_{len(attachments)+1}.{ext}"
                print(f"Generated filename from content-type: {filename}")
        
        # If we managed to identify a filename, treat it as attachment
        if filename:
            payload = part.get_payload(decode=True)
            if payload:
                payload_size = len(payload)
                print(f"Found attachment with fallback method: {filename}, size={payload_size} bytes")
                
                # Create temporary file
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, filename)
                
                # Save attachment data
                with open(file_path, 'wb') as f:
                    f.write(payload)
                
                print(f"Saved attachment to: {file_path}")
                
                # Add to list
                attachments.append({
                    'filename': filename,
                    'path': file_path,
                    'content_type': part.get_content_type(),
                    'size': payload_size
                })
            else:
                print(f"Warning: No payload for potential attachment: {filename}")
    
    print(f"Fallback method found {len(attachments)} attachment(s)")
    return attachments 