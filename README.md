# Email Support System

A Python-based email support system that integrates with Telegram and uses Ollama for AI-powered response processing.

## Features

- Email monitoring and processing
- Telegram bot integration for support team communication
- AI-powered response processing using Ollama
- Automatic ticket creation and management
- HTML email support
- Robust error handling and recovery

## Project Structure

```
email-support-system/
├── src/
│   ├── config/
│   │   └── settings.py         # Configuration and environment variables
│   ├── models/
│   │   └── ticket.py          # Ticket model and queue management
│   ├── services/
│   │   ├── email_service.py   # Email handling (SMTP/IMAP)
│   │   ├── ollama_service.py  # Ollama AI integration
│   │   └── telegram_service.py # Telegram bot functionality
│   ├── handlers/
│   │   └── telegram_handlers.py # Telegram command handlers
│   └── main.py                # Main application entry point
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   # Email Server Settings
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=587
   SMTP_USERNAME=your_email
   SMTP_PASSWORD=your_password
   IMAP_SERVER=your_imap_server
   IMAP_PORT=993
   IMAP_USERNAME=your_email
   IMAP_PASSWORD=your_password

   # Telegram Settings
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_SUPPORT_CHAT_ID=your_chat_id

   # Ollama Settings
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=your_model_name
   ```

## Usage

1. Start the application:
   ```bash
   python src/main.py
   ```

2. The system will:
   - Monitor the configured email inbox for new messages
   - Create tickets for new emails
   - Forward tickets to the configured Telegram chat
   - Process responses through Ollama before sending

3. Available Telegram commands:
   - `/help` - Show available commands
   - `/status` - Show current tickets in the queue
   - `/list` - List recent tickets
   - `/ticket ticket_id` - Show details of a specific ticket
   - `/reply ticket_id your_response` - Reply to a ticket

## Error Handling

The system includes comprehensive error handling for:
- Email server connection issues
- Telegram API errors
- Ollama processing failures
- Message formatting problems

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 