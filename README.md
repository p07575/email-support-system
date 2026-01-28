# 📧 AI Email Support System

An intelligent email support system with AI-powered auto-replies, smart email filtering, and Telegram integration.

## ✨ Features

- **🤖 AI Auto-Reply** - Automatically generates draft responses using RAG (Retrieval Augmented Generation)
- **🔍 Smart Filtering** - Auto-filters spam, promotions, and newsletters using AI classification
- **📚 Knowledge Base** - RAG system that reads your documents to provide accurate, contextual responses
- **📱 Telegram Integration** - Forward tickets to Telegram with one-click inline buttons for confirmation
- **🔌 OpenRouter Integration** - Uses free AI models via OpenRouter for classification and responses
- **📨 Email Monitoring** - Continuous IMAP inbox monitoring for new messages
- **🎫 Ticket Management** - Automatic ticket creation and tracking
- **🗄️ MySQL Database** - Persistent storage for tickets, responses, and drafts

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/yourusername/email-support-system.git
cd email-support-system

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Add your knowledge base documents
# Place .md, .txt, or .json files in knowledge_base/

# Start the system
docker-compose up -d

# View logs
docker-compose logs -f email-support
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up MySQL database
python setup_database.py

# Run the application
python main.py
```

## 📚 AI Features

### Email Classification
Automatically classifies incoming emails as:
- **Support Request** → Creates ticket, generates AI response
- **Promotion/Spam** → Auto-filtered, notification sent
- **Newsletter** → Auto-archived
- **Inquiry/Complaint** → High priority handling

### RAG Knowledge Base
Place your documents in the `knowledge_base/` folder:
- FAQ documents
- Product documentation
- Company policies
- Common response templates

The AI will use these documents to generate accurate, contextual responses.

### Auto-Reply Workflow
```
📧 Email Received
     ↓
🔍 AI Classification
     ↓
┌────────────────────────────────┐
│ Spam/Promo? → 🗑️ Auto-filter   │
│ Support?    → Continue ↓       │
└────────────────────────────────┘
     ↓
📚 RAG: Search Knowledge Base
     ↓
🤖 AI: Generate Draft Response
     ↓
📱 Telegram: Show with Buttons
     ↓
👆 You: Tap to Confirm/Edit
     ↓
📤 Email Sent to Customer
```

## 🏗️ Project Structure

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
├── knowledge_base/               # Your knowledge documents (gitignored)
├── docker-compose.yml            # Docker Compose config
├── Dockerfile                    # Docker build file
├── .env.example                  # Environment template
├── emailsys.sql                  # Database schema
├── setup_database.py             # Database setup
├── requirements.txt              # Dependencies
└── README.md
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

### Key Environment Variables

```env
# Email (IMAP/SMTP)
EMAIL_IMAP_SERVER=imap.example.com
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_USERNAME=support@example.com
EMAIL_PASSWORD=your_password

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# OpenRouter API (get free key at openrouter.ai)
OPENROUTER_API_KEY=your_api_key
OPENROUTER_CLASSIFIER_MODEL=meta-llama/llama-3.2-3b-instruct:free
OPENROUTER_RESPONSE_MODEL=meta-llama/llama-3.2-3b-instruct:free

# Features
AUTO_REPLY_ENABLED=true
AUTO_FILTER_ENABLED=true

# Database (Docker uses these automatically)
DB_HOST=mysql
DB_NAME=email_support
DB_USER=email_support
DB_PASSWORD=email_support_pass
```

### Free OpenRouter Models
- `meta-llama/llama-3.2-3b-instruct:free` - Good balance of speed and quality
- `meta-llama/llama-3.2-1b-instruct:free` - Faster, lighter
- `deepseek/deepseek-r1:free` - Reasoning model

Get your free API key at https://openrouter.ai/keys

## 🐳 Docker Deployment

### Docker Compose (Recommended)

```bash
# Start all services (app + MySQL)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

The Docker setup includes:
- **email-support**: Main application container
- **mysql**: MySQL 8.0 database (auto-initialized with schema)
- **Volumes**: Persistent storage for database and knowledge base

### Environment for Docker

When using Docker Compose, set these in your `.env`:

```env
# Database (connects to MySQL container)
DB_HOST=mysql
DB_PORT=3306
DB_NAME=email_support
DB_USER=email_support
DB_PASSWORD=email_support_pass

# MySQL root password (for container setup)
MYSQL_ROOT_PASSWORD=rootpassword
```

## 📱 Telegram Commands

### Inline Button Actions
| Button | Action |
|--------|--------|
| ✅ Send Draft | Send AI response immediately |
| 🔄 Regenerate | Generate new AI response |
| ✏️ Edit Draft | Modify and send |
| 📝 Custom Reply | Write your own response |
| 🗑️ Archive | Archive without responding |

### Text Commands
| Command | Description |
|---------|-------------|
| `/status` | Show active tickets |
| `/list` | List recent tickets |
| `/ticket <id>` | View ticket details |
| `/reply <id> <msg>` | Send custom reply |
| `/help` | Show help message |

### Knowledge Base Commands
| Command | Description |
|---------|-------------|
| `/kb list` | List knowledge base documents |
| `/kb add` | How to add documents |
| `/kb reload` | Reload documents |

## 📚 Knowledge Base

Add documents to the `knowledge_base/` folder:

```
knowledge_base/
├── faq.md           # Frequently asked questions
├── products.txt     # Product information
├── policies.md      # Company policies
└── troubleshooting.md
```

Supported formats: `.txt`, `.md`, `.json`

**Note**: The `knowledge_base/` folder is gitignored since it may contain private company information.

## 🗄️ Database Setup

### Using Docker (Automatic)
Docker Compose automatically sets up MySQL with the schema.

### Manual Setup

```bash
# Run setup script
python setup_database.py
```

Or manually:

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE email_support;

-- Create user and grant privileges
CREATE USER 'email_support'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON email_support.* TO 'email_support'@'%';
FLUSH PRIVILEGES;
```

## 🔒 Security Notes

- Never commit `.env` file
- Knowledge base is gitignored (may contain sensitive info)
- Docker runs as non-root user
- Use strong passwords for MySQL
- Consider using secrets management in production

## 🛠️ Error Handling

The system includes comprehensive error handling for:
- Email server connection issues
- Telegram API errors
- AI service failures (with retry logic)
- Database connection issues
- Message formatting problems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Made with ❤️ for efficient customer support