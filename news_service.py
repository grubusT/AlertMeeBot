import json
import requests
import time
from datetime import datetime
from config import *
import nltk
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# Initialize sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

# Track news articles sent in ALERTS only, not for /latest commands
alert_sent_articles = []
last_check_time = datetime.now()

def analyze_sentiment(text):
    """Analyze the sentiment of a text and return category and score."""
    if not text:
        return "neutral", 0.0
    
    scores = sentiment_analyzer.polarity_scores(text)
    compound_score = scores['compound']
    
    # Categorize based on compound score
    if compound_score >= POSITIVE_THRESHOLD:
        category = "positive"
    elif compound_score <= NEGATIVE_THRESHOLD:
        category = "negative"
    else:
        category = "neutral"
    
    return category, compound_score

def get_sentiment_emoji(sentiment):
    """Get an emoji representing the sentiment."""
    return SENTIMENT_EMOJIS.get(sentiment, "⚪")  # Default to neutral/white circle

async def fetch_trump_news(for_alerts=False):
    """Fetch news about Trump from Alpha Vantage API."""
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
                    # Analyze sentiment of the title and summary
                    title_sentiment, title_score = analyze_sentiment(article.get("title", ""))
                    summary_sentiment, summary_score = analyze_sentiment(article.get("summary", ""))
                    
                    # Calculate overall sentiment based on both title and summary
                    # Give more weight to summary as it contains more information
                    if summary:
                        overall_sentiment = summary_sentiment
                        overall_score = summary_score
                    else:
                        overall_sentiment = title_sentiment
                        overall_score = title_score
                    
                    # Add sentiment data to article
                    article["sentiment"] = {
                        "category": overall_sentiment,
                        "score": overall_score,
                        "title_sentiment": title_sentiment,
                        "summary_sentiment": summary_sentiment
                    }
                    
                    trump_articles.append(article)
        
        # If this is for automatic alerts, filter out previously sent articles
        if for_alerts:
            known_urls = [article["url"] for article in alert_sent_articles]
            new_articles = [article for article in trump_articles if article["url"] not in known_urls]
            
            # Update tracking for alert articles only
            alert_sent_articles.extend(new_articles)  # Add only new articles
            alert_sent_articles = alert_sent_articles[:MAX_STORED_ARTICLES]  # Keep last N articles
            last_check_time = current_time
            
            # Save alert article tracking to file for persistence
            save_alert_articles()
            
            return new_articles
        else:
            # For manual /latest requests, return all recent Trump articles without filtering
            return trump_articles[:MAX_ARTICLES_PER_REQUEST]  # Limit to N most recent articles
    
    except Exception as e:
        print(f"Error fetching news from Alpha Vantage: {e}")
        return []

async def fetch_voo_price():
    """Fetch the latest stock price of VOO using Alpha Vantage."""
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
            print("Error fetching VOO data: No 'Global Quote' found in response")
            return None
    except Exception as e:
        print(f"Error fetching VOO data: {e}")
        return None

def format_published_time(time_str):
    """Format the published time to a more readable format."""
    try:
        time_obj = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        return time_obj.strftime("%B %d, %Y at %H:%M")
    except:
        return time_str

def save_alert_articles():
    """Save alert article history to a file"""
    articles_to_save = []
    for article in alert_sent_articles[:MAX_STORED_ARTICLES]:  # Save only last N
        # Save only essential fields to reduce file size
        sentiment_data = article.get("sentiment", {})
        articles_to_save.append({
            "url": article["url"],
            "title": article.get("title", ""),
            "sentiment": {
                "category": sentiment_data.get("category", "neutral"),
                "score": sentiment_data.get("score", 0)
            }
        })
    
    with open(ALERT_ARTICLES_FILE, "w") as f:
        json.dump(articles_to_save, f)

def load_alert_articles():
    """Load alert article history from a file"""
    global alert_sent_articles
    try:
        with open(ALERT_ARTICLES_FILE, "r") as f:
            alert_sent_articles = json.load(f)
        print(f"Loaded {len(alert_sent_articles)} previously sent articles")
    except FileNotFoundError:
        alert_sent_articles = []
        print("No article history file found, starting with empty list")

def format_news_message(article, include_alert_header=False, include_voo_data=None):
    """Format a news article into a message ready to be sent."""
    sentiment = article.get("sentiment", {})
    sentiment_category = sentiment.get("category", "neutral")
    sentiment_emoji = get_sentiment_emoji(sentiment_category)
    sentiment_score = sentiment.get("score", 0)
    
    # Start with alert header if requested
    if include_alert_header:
        news_text = f"🚨 *TRUMP NEWS ALERT* {sentiment_emoji}\n\n"
    else:
        news_text = f"{sentiment_emoji} "
    
    # Add title and summary
    news_text += f"*{article['title']}*\n\n"
    if article.get('summary'):
        news_text += f"{article['summary']}\n\n"
    
    # Add sentiment analysis information
    news_text += f"*Sentiment Analysis*: {sentiment_category.capitalize()} (Score: {sentiment_score:.2f})\n\n"
        
    # Add source and time information if available
    if article.get('source'):
        news_text += f"Source: {article['source']}\n"
    if article.get('time_published'):
        formatted_time = format_published_time(article['time_published'])
        news_text += f"Published: {formatted_time}\n"
            
    news_text += f"\n[Read full article]({article['url']})"
    
    # Append VOO tracker information if provided
    if include_voo_data:
        if include_voo_data.get('price'):
            news_text += (
                "\n\n📈 *VOO Tracker*\n"
                f"Price: ${include_voo_data['price']}\n"
                f"Change: {include_voo_data['change']} ({include_voo_data['change_percent']})\n"
            )
        else:
            news_text += "\n\n📈 *VOO Tracker*\nUnable to fetch VOO data at the moment.\n"
    
    return news_text
