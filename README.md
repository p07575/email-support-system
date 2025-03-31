# Email Support System

An automated email support system that routes customer emails to Telegram and processes responses with AI.

## Features

- Automatically checks for new support emails
- Sends acknowledgment emails to customers
- Forwards emails to a Telegram chat for support agents
- Uses Ollama for AI-enhanced response generation
- Formats emails properly for professional communication

## Requirements

- Python 3.8+
- Email account with SMTP/IMAP access
- Telegram Bot Token
- Ollama server running with desired model

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your `.env` file with credentials:

```
# Email Server Settings
SMTP_SERVER=your.smtp.server
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your_password
IMAP_SERVER=your.imap.server
IMAP_PORT=993
IMAP_USERNAME=your@email.com
IMAP_PASSWORD=your_password

# Telegram Settings
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_SUPPORT_CHAT_ID=your_chat_id

# Ollama Settings
OLLAMA_HOST=http://your.ollama.server:11434
OLLAMA_MODEL=your/model:tag
```

## Usage

1. Start the system:

```bash
python main.py
```

2. The system will:
   - Check for new emails every minute
   - Send acknowledgments to customers
   - Forward emails to your Telegram support chat

3. Telegram commands:
   - `/reply ticket_id your_response` - Reply to a customer
   - `/status` - Show current tickets in the queue
   - `/list` - List all recent tickets
   - `/ticket ticket_id` - Show details of a specific ticket
   - `/help` - Show help message

## How It Works

1. Email Monitoring: Continuously monitors the specified email account for new messages
2. Ticket Creation: Each email is assigned a unique ticket ID
3. Telegram Notification: Support agents are notified via Telegram
4. AI Response Processing: Agent responses are improved by Ollama AI
5. Customer Communication: Formatted responses are sent to the customer

## Troubleshooting

- **Ollama Connection Issues**: Ensure your Ollama server is running and accessible
- **Telegram Bot Errors**: Make sure your bot token is correct and the bot is added to the chat
- **Email Authentication Failures**: Verify your email credentials and server settings 