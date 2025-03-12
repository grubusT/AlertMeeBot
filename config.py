import os
from dotenv import load_dotenv

# Load environment variables from .env file 
load_dotenv()

#.env file stored securely
API_KEY = os.getenv("API_KEY") 
SECRET_KEY = os.getenv("SECRET_KEY")

# News service configuration
CHECK_INTERVAL = 900  # 15 minutes
MAX_ARTICLES_ALERT = 3
MAX_ARTICLES_LATEST = 5
