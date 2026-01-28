import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email server settings
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER")
EMAIL_IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", "993"))
EMAIL_CHECK_INTERVAL = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# Ollama Settings (kept for backward compatibility)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# OpenRouter Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Free model for classification (structured output)
OPENROUTER_CLASSIFIER_MODEL = os.getenv("OPENROUTER_CLASSIFIER_MODEL", "google/gemma-3-4b-it:free")
# Model for response generation
OPENROUTER_RESPONSE_MODEL = os.getenv("OPENROUTER_RESPONSE_MODEL", "google/gemma-3-4b-it:free")

# RAG Settings
RAG_KNOWLEDGE_DIR = os.getenv("RAG_KNOWLEDGE_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "knowledge_base"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))

# Auto-reply Settings
AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "true").lower() == "true"
AUTO_FILTER_ENABLED = os.getenv("AUTO_FILTER_ENABLED", "true").lower() == "true"

# MySQL Settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "email_support")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password")
DB_NAME = os.getenv("DB_NAME", "email_support") 