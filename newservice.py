import json #api key not yet commited
import requests
from datetime import datetime, timedelta 
from config import ALPHA_VANTAGE_API_KEY

async def fetch_trump_news(for_alerts=False):
    global last_check_time, alert_sent_articles
    
    # Calculate time since last check
    current_time = datetime.now()
    
    # Use Alpha Vantage's News API
    url = "https://www.alphavantage.co/query"
    
    # Set parameters for the API request
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": "politics",  # Filter by politics topic
        "apikey": ALPHA_VANTAGE_API_KEY,
        "tickers": "",  # We don't need stock tickers
        "sort": "LATEST"
    }
    
    try:
        response = requests.get(url, params=params)
        news_data = response.json()
        
        trump_articles = []
        
        if "feed" in news_data:
            for article in news_data["feed"]:
                # Check if the article contains "Trump" in title, summary or other relevant fields
                title = article.get("title", "").lower()
                summary = article.get("summary", "").lower()
                
                if "trump" in title or "trump" in summary:
                    trump_articles.append(article)
        
        # If this is for automatic alerts, filter out previously sent articles
        if for_alerts:
            known_urls = [article["url"] for article in alert_sent_articles]
            new_articles = [article for article in trump_articles if article["url"] not in known_urls]
            
            # Update tracking for alert articles only
            last_check_time = current_time
            alert_sent_articles = new_articles + alert_sent_articles[:50]  # Keep last 50 articles
            
            return new_articles
        else:
            # For manual /latest requests, return all recent Trump articles without filtering
            return trump_articles[:5]  # Limit to 5 most recent articles
    
    except Exception as e:
        print(f"Error fetching news from Alpha Vantage: {e}")
        return []

# Add a simple way to store subscribers
def save_subscribers():
    """Save subscribers to a file"""
    with open("subscribers.json", "w") as f:
        json.dump(list(subscribers), f)

def load_subscribers():
    """Load subscribers from a file"""
    global subscribers
    try:
        with open("subscribers.json", "r") as f:
            subscribers = set(json.load(f))
    except FileNotFoundError:
        subscribers = set()
