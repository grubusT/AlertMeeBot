import os
from dotenv import load_dotenv

# Load environment variables from .env file 
load_dotenv()

#.env file stored securely
API_KEY = os.getenv("API_KEY") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# News service configuration
CHECK_INTERVAL = 900  # 15 minutes
MAX_ARTICLES_ALERT = 3
MAX_ARTICLES_LATEST = 5
