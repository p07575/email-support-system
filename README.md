# Email Support System

A Python-based email support system that integrates with Telegram and uses AI for automated response generation, email classification, and knowledge-based replies.

## Features

- **AI-Powered Auto-Reply**: Automatically generates draft responses using RAG (Retrieval Augmented Generation)
- **Smart Email Filtering**: Auto-filters spam, promotions, and newsletters using AI classification
- **Knowledge Base**: RAG system that reads your documents to provide accurate, contextual responses
- **Telegram Integration**: Forward tickets to Telegram with one-click confirmation for AI drafts
- **OpenRouter Integration**: Uses free AI models via OpenRouter for classification and responses
- **Email Monitoring**: Continuous IMAP inbox monitoring for new messages
- **Ticket Management**: Automatic ticket creation and tracking
- **MySQL Database**: Persistent storage for tickets, responses, and drafts

## New AI Features

### 1. Email Classification
Automatically classifies incoming emails as:
- **Support Request** → Creates ticket, generates AI response
- **Promotion/Spam** → Auto-filtered, notification sent
- **Newsletter** → Auto-archived
- **Inquiry/Complaint** → High priority handling

### 2. RAG Knowledge Base
Place your documents in the `knowledge_base/` folder:
- FAQ documents
- Product documentation
- Company policies
- Common response templates

The AI will use these documents to generate accurate, contextual responses.

### 3. Auto-Reply with Confirmation
1. New email arrives
2. AI classifies the email
3. AI generates draft response using knowledge base
4. Draft sent to Telegram for your confirmation
5. One-click to send or edit

## Project Structure

```
email-support-system/
├── src/
│   ├── config/
│   │   └── settings.py           # Configuration and environment variables
│   ├── models/
│   │   └── ticket.py             # Ticket model
│   ├── services/
│   │   ├── email_service.py      # Email handling (SMTP/IMAP)
│   │   ├── openrouter_service.py # OpenRouter AI integration
│   │   ├── email_classifier_service.py # Email classification
│   │   ├── rag_service.py        # RAG knowledge base
│   │   ├── ollama_service.py     # Ollama fallback
│   │   ├── telegram_service.py   # Telegram bot
│   │   └── db_service.py         # MySQL database
│   ├── handlers/
│   │   └── telegram_handlers.py  # Telegram commands
│   └── main.py                   # Main application
├── knowledge_base/               # Your knowledge documents
├── .env.example                  # Environment template
├── emailsys.sql                  # Database schema
├── setup_database.py             # Database setup
├── requirements.txt              # Dependencies
└── README.md
```

## Setup

1. Clone the repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

4. Get your OpenRouter API key from https://openrouter.ai/keys

5. Set up the MySQL database:
   ```bash
   python setup_database.py
   ```

6. Add documents to `knowledge_base/` folder

7. Start the application:
   ```bash
   python main.py
   ```

## Configuration

### Key Environment Variables

```env
# OpenRouter (for AI features)
OPENROUTER_API_KEY=your_key
OPENROUTER_CLASSIFIER_MODEL=google/gemma-3-4b-it:free
OPENROUTER_RESPONSE_MODEL=google/gemma-3-4b-it:free

# Auto Features
AUTO_REPLY_ENABLED=true    # AI generates draft responses
AUTO_FILTER_ENABLED=true   # Filter spam/promotions

# Knowledge Base
RAG_KNOWLEDGE_DIR=./knowledge_base
RAG_CHUNK_SIZE=500
```

### Free OpenRouter Models
- `google/gemma-3-4b-it:free` - Good for both classification and responses
- `meta-llama/llama-3.2-1b-instruct:free` - Faster, lighter
- `meta-llama/llama-3.2-3b-instruct:free` - Better quality

See `.env.example` for all configuration options.

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
   - Classify emails and filter spam/promotions
   - Generate AI draft responses using knowledge base
   - Forward tickets to Telegram for confirmation

## Telegram Commands

### AI Auto-Reply Commands
| Command | Description |
|---------|-------------|
| `/confirm ticket_id` | Send the AI-generated draft |
| `/edit ticket_id changes` | Edit the draft and send |
| `/regenerate ticket_id` | Generate a new AI response |

### Manual Commands
| Command | Description |
|---------|-------------|
| `/reply ticket_id response` | Write custom response |
| `/status` | Show active tickets |
| `/list` | List recent tickets |
| `/ticket ticket_id` | Show ticket details |
| `/help` | Show help message |

### Knowledge Base Commands
| Command | Description |
|---------|-------------|
| `/kb list` | List knowledge base documents |
| `/kb add` | How to add documents |
| `/kb reload` | Reload documents |

## Workflow

### With Auto-Reply Enabled
1. 📧 Email received
2. 🔍 AI classifies email (spam → filtered, support → continue)
3. 📚 RAG searches knowledge base for relevant context
4. 🤖 AI generates draft response
5. 📱 Telegram notification with draft
6. ✅ You confirm with `/confirm` or edit with `/edit`
7. 📤 Response sent to customer

### Manual Mode
Set `AUTO_REPLY_ENABLED=false` in `.env` for manual mode.

## Knowledge Base

Add documents to the `knowledge_base/` folder:

```
knowledge_base/
├── faq.md           # Frequently asked questions
├── products.txt     # Product information
├── policies.json    # Company policies
└── templates/
    └── common_responses.md
```

Supported formats: `.txt`, `.md`, `.json`

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