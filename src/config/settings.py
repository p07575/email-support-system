import os
from dotenv import load_dotenv

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

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_SUPPORT_CHAT_ID = os.getenv("TELEGRAM_SUPPORT_CHAT_ID")

# Ollama Settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") 