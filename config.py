import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file 
load_dotenv()

# API Tokens and Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY") 

# News Check Configuration
NEWS_CHECK_INTERVAL = 900  # 15 minutes in seconds
FIRST_CHECK_DELAY = 10  # Seconds to wait before first check

# File paths for persistent storage
SUBSCRIBERS_FILE = "subscribers.json"
ARTICLES_HISTORY_FILE = "alert_articles.json"

# News fetch configuration
MAX_ALERTS_PER_CHECK = 3
MAX_LATEST_ARTICLES = 5
MAX_TRACKED_ARTICLES = 50

# Print a timestamp message
def log_message(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
