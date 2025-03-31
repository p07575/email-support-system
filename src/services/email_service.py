import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import re
from typing import Optional, Tuple
from ..config.settings import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    IMAP_SERVER, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD
)

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

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an email using SMTP"""
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

def extract_email_details(email_message: email.message.Message) -> Tuple[str, str, str]:
    """Extract email details from an email message"""
    # Extract subject
    subject = decode_header(email_message["subject"])[0][0]
    if isinstance(subject, bytes):
        subject = subject.decode()
    
    # Extract from email
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
    
    return from_email, subject, body

def check_new_emails(callback) -> None:
    """Check for new emails and call the callback function for each new email"""
    try:
        print("Checking for new emails...")
        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT) as imap:
            imap.login(IMAP_USERNAME, IMAP_PASSWORD)
            imap.select('INBOX')
            
            # Search for unread emails
            _, message_numbers = imap.search(None, 'UNSEEN')
            
            num_messages = len(message_numbers[0].split())
            if num_messages > 0:
                print(f"Found {num_messages} new email(s)")
            else:
                print("No new emails")
            
            for num in message_numbers[0].split():
                print(f"Processing email #{num}...")
                _, msg_data = imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract email details
                from_email, subject, body = extract_email_details(email_message)
                
                # Convert HTML body to plain text if needed
                plain_body = body
                if '<html' in body.lower() or '<div' in body.lower() or '<p' in body.lower():
                    plain_body = html_to_text(body)
                
                # Call the callback function with the email details
                callback(from_email, subject, body, plain_body)
                
    except Exception as e:
        print(f"Error checking emails: {str(e)}")

def send_response_email(to_email: str, ticket_id: str, response_text: str) -> bool:
    """Send a response email to a customer"""
    html_content = f"""
    <h1>Response to your support request</h1>
    <p>This is a response to your support ticket (#{ticket_id}).</p>
    <div style="white-space: pre-wrap;">{response_text}</div>
    """
    
    return send_email(to_email, f"Re: Support Ticket #{ticket_id}", html_content) 