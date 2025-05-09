# Email Support System

A Python-based email support system that integrates with Telegram and uses Ollama for AI-powered response processing.

## Features

- Email monitoring and processing
- Telegram bot integration for support team communication
- AI-powered response processing using Ollama
- Automatic ticket creation and management
- HTML email support
- Robust error handling and recovery
- MySQL database for ticket storage

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
│   │   ├── telegram_service.py # Telegram bot functionality
│   │   └── db_service.py      # MySQL database service
│   ├── handlers/
│   │   └── telegram_handlers.py # Telegram command handlers
│   └── main.py                # Main application entry point
├── .env                       # Environment variables
├── emailsys.sql               # Database schema
├── setup_database.py          # Database setup script
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
   EMAIL_SMTP_SERVER=your_smtp_server
   EMAIL_SMTP_PORT=587
   EMAIL_USERNAME=your_email
   EMAIL_PASSWORD=your_password
   EMAIL_IMAP_SERVER=your_imap_server
   EMAIL_IMAP_PORT=993
   EMAIL_CHECK_INTERVAL=60  # in seconds

   # Telegram Settings
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_SUPPORT_CHAT_ID=your_chat_id

   # Ollama Settings
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=your_model_name
   
   # MySQL Settings
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=email_support
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=email_support
   ```

## MySQL Database Setup

This application uses MySQL to store ticket data. Before running the application, you need to set up the database:

1. Make sure MySQL server is installed and running
2. Update the `.env` file with your MySQL credentials (see above)
3. Run the database setup script:
   ```bash
   python setup_database.py
   ```
4. The script will create the necessary database and tables automatically

### MySQL Setup Example

If you need to create a new MySQL user and database for this application:

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE email_support;

-- Create user and grant privileges
CREATE USER 'email_support'@'%' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON email_support.* TO 'email_support'@'%';
FLUSH PRIVILEGES;

-- Exit MySQL
EXIT;
```

Then update your `.env` file with these credentials:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=email_support
MYSQL_PASSWORD=your_strong_password
MYSQL_DATABASE=email_support
```

For remote MySQL servers, change `MYSQL_HOST` to the server's IP address.

## Usage

1. Start the application:
   ```bash
   python main.py
   ```

2. The system will:
   - Monitor the configured email inbox for new messages
   - Create tickets for new emails
   - Forward tickets to the configured Telegram chat
   - Process responses through Ollama before sending

3. Available Telegram commands:
   - `/help` - Show available commands
   - `/status` - Show current tickets in the queue (excluding responded ones)
   - `/list` - List recent tickets with received and response times
   - `/ticket ticket_id` - Show details of a specific ticket
   - `/reply ticket_id your_response` - Reply to a ticket

## Error Handling

The system includes comprehensive error handling for:
- Email server connection issues
- Telegram API errors
- Ollama processing failures
- Message formatting problems
- Database connection issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.