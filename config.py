import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file 
load_dotenv()

# API Tokens and Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY") 

# Alerts configuration
NEWS_CHECK_INTERVAL = 900  # 15 minutes in seconds
NEWS_CHECK_INITIAL_DELAY = 10  # seconds

# File paths for persistent storage
SUBSCRIBERS_FILE = "subscribers.json"
ARTICLES_HISTORY_FILE = "alert_articles.json"
USER_PREFERENCES_FILE = "user_preferences.json"

# News fetch configuration
MAX_ALERTS_PER_CHECK = 3
MAX_LATEST_ARTICLES = 5
MAX_TRACKED_ARTICLES = 50

# Sentiment score thresholds
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

# Sentiment Emojis
SENTIMENT_EMOJIS = {
    "positive": "🟢",  # green circle
    "negative": "🔴",  # red circle
    "neutral": "⚪"    # white circle
}

# Print a timestamp message
def log_message(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
