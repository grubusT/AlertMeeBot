import json
import requests
from datetime import datetime
from config import ALPHA_VANTAGE_API_KEY, ARTICLES_HISTORY_FILE, MAX_TRACKED_ARTICLES, MAX_LATEST_ARTICLES, log_message

# Global variables
alert_sent_articles = []
last_check_time = datetime.now()

async def fetch_trump_news(for_alerts=False):
    """
    Fetch news articles related to Trump from Alpha Vantage.
    
    Args:
        for_alerts (bool): If True, filter out previously sent articles
        
    Returns:
        list: A list of Trump-related news articles
    """
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
            alert_sent_articles.extend(new_articles)  # Add only new articles
            alert_sent_articles = alert_sent_articles[:MAX_TRACKED_ARTICLES]  # Keep last N articles
            last_check_time = current_time
            
            # Save alert article tracking to file for persistence
            save_alert_articles()
            
            return new_articles
        else:
            # For manual /latest requests, return all recent Trump articles without filtering
            return trump_articles[:MAX_LATEST_ARTICLES]  # Limit to N most recent articles
    
    except Exception as e:
        log_message(f"Error fetching news from Alpha Vantage: {e}")
        return []


async def fetch_voo_price():
    """
    Fetch the latest stock price of VOO using Alpha Vantage.
    
    Returns:
        dict or None: A dictionary with price information or None if fetching fails
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": "VOO",
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "Global Quote" in data:
            voo_data = data["Global Quote"]
            return {
                "price": voo_data.get("05. price", "N/A"),
                "change": voo_data.get("09. change", "N/A"),
                "change_percent": voo_data.get("10. change percent", "N/A"),
            }
        else:
            log_message("Error fetching VOO data: No 'Global Quote' found in response")
            return None
    except Exception as e:
        log_message(f"Error fetching VOO data: {e}")
        return None


def format_article_message(article, voo_data, is_alert=False):
    """
    Format a news article into a Telegram message.
    
    Args:
        article (dict): The article data
        voo_data (dict): VOO price data
        is_alert (bool): Whether this is for an alert (adds alert header)
        
    Returns:
        str: Formatted message text
    """
    # Start with alert header if this is an alert
    news_text = ""
    if is_alert:
        news_text = f"🚨 *TRUMP NEWS ALERT*\n\n"
    
    # Add article title
    news_text += f"📰 *{article['title']}*\n\n"
    
    # Add summary if available
    if article.get('summary'):
        news_text += f"{article['summary']}\n\n"
        
    # Add source and time information if available
    if article.get('source'):
        news_text += f"Source: {article['source']}\n"
    
    if article.get('time_published'):
        # Format time_published if needed
        try:
            time_str = article['time_published']
            time_obj = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
            formatted_time = time_obj.strftime("%B %d, %Y at %H:%M")
            news_text += f"Published: {formatted_time}\n"
        except:
            news_text += f"Published: {article['time_published']}\n"
            
    # Add article link
    news_text += f"\n[Read full article]({article['url']})"
    
    # Append VOO tracker information
    news_text += format_voo_message(voo_data)
    
    return news_text


def format_voo_message(voo_data):
    """
    Format VOO price data into a message.
    
    Args:
        voo_data (dict or None): VOO price data
        
    Returns:
        str: Formatted VOO message
    """
    if voo_data:
        return (
            "\n\n📈 *VOO Tracker*\n"
            f"Price: ${voo_data['price']}\n"
            f"Change: {voo_data['change']} ({voo_data['change_percent']})\n"
        )
    else:
        return "\n\n📈 *VOO Tracker*\nUnable to fetch VOO data at the moment.\n"


def save_alert_articles():
    """Save alert article history to a file"""
    articles_to_save = []
    for article in alert_sent_articles[:MAX_TRACKED_ARTICLES]:  # Save only last N
        # Save only essential fields to reduce file size
        articles_to_save.append({
            "url": article["url"],
            "title": article.get("title", "")
        })
    
    with open(ARTICLES_HISTORY_FILE, "w") as f:
        json.dump(articles_to_save, f)


def load_alert_articles():
    """Load alert article history from a file"""
    global alert_sent_articles
    try:
        with open(ARTICLES_HISTORY_FILE, "r") as f:
            alert_sent_articles = json.load(f)
        log_message(f"Loaded {len(alert_sent_articles)} previously sent articles")
    except FileNotFoundError:
        alert_sent_articles = []
        log_message("No article history file found, starting with empty list")
