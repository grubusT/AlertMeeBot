import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from config import *
from news_service import (
    fetch_trump_news,
    fetch_voo_price,
    format_news_message,
    load_alert_articles,
    save_alert_articles
)

# Track users subscribed to alerts
subscribers = set()

# User preferences - default to all sentiments
user_preferences = {}  # {user_id: {"sentiments": ["positive", "neutral", "negative"]}}

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bot."""
    user_id = update.effective_user.id
    subscribers.add(user_id)
    
    # Initialize user preferences if not already set
    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "sentiments": ["positive", "neutral", "negative"]  # Default to all sentiments
        }
    
    save_subscribers()  # Save after adding subscriber
    save_user_preferences()  # Save user preferences
    
    # Create sentiment filter buttons
    keyboard = [
        [
            InlineKeyboardButton("Set Sentiment Filters", callback_data="set_sentiment_filters")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Welcome to the Trump News Alert Bot with Sentiment Analysis!\n\n"
        "You are now subscribed to Trump news alerts. You'll receive notifications when significant news about Trump is published.\n\n"
        "Each news article is analyzed for sentiment (positive, neutral, or negative).\n\n"
        "Commands:\n"
        "/stop - Unsubscribe from alerts\n"
        "/latest - Get the latest Trump news\n"
        "/preferences - Set your sentiment preferences\n"
        "/help - Show available commands",
        reply_markup=reply_markup
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from alerts."""
    user_id = update.effective_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers()  # Save after removing subscriber
    
    await update.message.reply_text("You've unsubscribed from Trump news alerts. Send /start to subscribe again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "📰 Trump News Alert Bot Commands:\n\n"
        "/start - Subscribe to Trump news alerts\n"
        "/stop - Unsubscribe from alerts\n"
        "/latest - Get the latest Trump news\n"
        "/preferences - Set your sentiment preferences\n"
        "/help - Show this help message\n\n"
        "Sentiment Indicators:\n"
        "🟢 - Positive news\n"
        "⚪ - Neutral news\n"
        "🔴 - Negative news"
    )

async def preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and set user preferences."""
    user_id = update.effective_user.id
    
    # Create buttons for sentiment selection
    keyboard = [
        [
            InlineKeyboardButton("Positive News 🟢", callback_data="toggle_positive"),
            InlineKeyboardButton("Neutral News ⚪", callback_data="toggle_neutral")
        ],
        [
            InlineKeyboardButton("Negative News 🔴", callback_data="toggle_negative"),
            InlineKeyboardButton("All News", callback_data="select_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check current preferences
    current_prefs = user_preferences.get(user_id, {"sentiments": ["positive", "neutral", "negative"]})
    selected_sentiments = current_prefs["sentiments"]
    
    sentiment_status = {
        "positive": "🟢 Positive news: " + ("Enabled ✅" if "positive" in selected_sentiments else "Disabled ❌"),
        "neutral": "⚪ Neutral news: " + ("Enabled ✅" if "neutral" in selected_sentiments else "Disabled ❌"),
        "negative": "🔴 Negative news: " + ("Enabled ✅" if "negative" in selected_sentiments else "Disabled ❌")
    }
    
    preferences_text = (
        "📊 Your News Preferences\n\n"
        f"{sentiment_status['positive']}\n"
        f"{sentiment_status['neutral']}\n"
        f"{sentiment_status['negative']}\n\n"
        "Click below to toggle your preferences:"
    )
    
    await update.message.reply_text(preferences_text, reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses for preferences."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Initialize user preferences if not already set
    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "sentiments": ["positive", "neutral", "negative"]
        }
    
    current_prefs = user_preferences[user_id]
    selected_sentiments = current_prefs["sentiments"]
    
    if callback_data == "set_sentiment_filters":
        # Redirect to preferences command
        await preferences(update, context)
        return
    
    # Toggle sentiment preferences
    if callback_data == "toggle_positive":
        if "positive" in selected_sentiments:
            selected_sentiments.remove("positive")
        else:
            selected_sentiments.append("positive")
    elif callback_data == "toggle_neutral":
        if "neutral" in selected_sentiments:
            selected_sentiments.remove("neutral")
        else:
            selected_sentiments.append("neutral")
    elif callback_data == "toggle_negative":
        if "negative" in selected_sentiments:
            selected_sentiments.remove("negative")
        else:
            selected_sentiments.append("negative")
    elif callback_data == "select_all":
        selected_sentiments = ["positive", "neutral", "negative"]
    
    # Make sure at least one is selected
    if not selected_sentiments:
        selected_sentiments = ["positive", "neutral", "negative"]
        await query.message.reply_text("⚠️ You must select at least one sentiment type. Resetting to all types.")
    
    user_preferences[user_id]["sentiments"] = selected_sentiments
    save_user_preferences()
    
    # Update the message with current preferences
    sentiment_status = {
        "positive": "🟢 Positive news: " + ("Enabled ✅" if "positive" in selected_sentiments else "Disabled ❌"),
        "neutral": "⚪ Neutral news: " + ("Enabled ✅" if "neutral" in selected_sentiments else "Disabled ❌"),
        "negative": "🔴 Negative news: " + ("Enabled ✅" if "negative" in selected_sentiments else "Disabled ❌")
    }
    
    preferences_text = (
        "📊 Your News Preferences\n\n"
        f"{sentiment_status['positive']}\n"
        f"{sentiment_status['neutral']}\n"
        f"{sentiment_status['negative']}\n\n"
        "Click below to toggle your preferences:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("Positive News 🟢", callback_data="toggle_positive"),
            InlineKeyboardButton("Neutral News ⚪", callback_data="toggle_neutral")
        ],
        [
            InlineKeyboardButton("Negative News 🔴", callback_data="toggle_negative"),
            InlineKeyboardButton("All News", callback_data="select_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=preferences_text, reply_markup=reply_markup)

async def get_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send latest Trump news on demand."""
    await update.message.reply_text("Fetching the latest Trump news... ⏳")
    
    # Get user ID for preference filtering
    user_id = update.effective_user.id
    user_prefs = user_preferences.get(user_id, {"sentiments": ["positive", "neutral", "negative"]})
    selected_sentiments = user_prefs["sentiments"]
    
    # Fetch Trump news articles
    articles = await fetch_trump_news(for_alerts=False)
    
    if not articles:
        await update.message.reply_text("No recent Trump news found. Try again later.")
        return
    
    # Filter articles based on user sentiment preferences
    filtered_articles = [a for a in articles if a.get("sentiment", {}).get("category") in selected_sentiments]
    
    if not filtered_articles:
        all_sentiments = [a.get("sentiment", {}).get("category", "unknown") for a in articles]
        await update.message.reply_text(
            f"Found {len(articles)} articles, but none match your sentiment preferences. "
            f"Available sentiments in recent news: {', '.join(set(all_sentiments))}.\n"
            f"Use /preferences to adjust your settings."
        )
        return
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Send up to MAX_ARTICLES_PER_REQUEST latest articles that match sentiment preferences
    for article in filtered_articles[:MAX_ARTICLES_PER_REQUEST]:
        news_text = format_news_message(article, include_alert_header=False, include_voo_data=voo_data)
        await update.message.reply_text(news_text, parse_mode="Markdown")

# Periodic news check and alert function
async def check_news_and_alert(context: ContextTypes.DEFAULT_TYPE):
    """Check for new Trump news and send alerts to subscribers."""
    print(f"Running scheduled news check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not subscribers:
        print("No subscribers to alert")
        return  # No subscribers to alert
    
    # Fetch new Trump news articles
    articles = await fetch_trump_news(for_alerts=True)
    
    if not articles:
        print("No new articles found")
        return  # No new articles
    
    print(f"Found {len(articles)} new articles to send as alerts")
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Send notifications to subscribers based on their preferences (limit to MAX_ARTICLES_PER_ALERT newest articles)
    for article in articles[:MAX_ARTICLES_PER_ALERT]:
        sentiment_category = article.get("sentiment", {}).get("category", "neutral")
        
        news_text = format_news_message(article, include_alert_header=True, include_voo_data=voo_data)
        
        for user_id in subscribers:
            # Check user's sentiment preferences
            user_prefs = user_preferences.get(user_id, {"sentiments": ["positive", "neutral", "negative"]})
            if sentiment_category in user_prefs["sentiments"]:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=news_text,
                        parse_mode="Markdown"
                    )
                    print(f"Sent {sentiment_category} alert to user {user_id}")
                except Exception as e:
                    print(f"Failed to send alert to user {user_id}: {e}")
            else:
                print(f"Skipped {sentiment_category} alert for user {user_id} due to preferences")

# Function to manually check news periodically if job queue isn't available
async def manual_news_check(application):
    """Manual implementation of periodic news checks if job queue isn't available"""
    print("Starting manual news checker backup system")
    while True:
        try:
            # Wait for NEWS_CHECK_INTERVAL between checks
            await asyncio.sleep(NEWS_CHECK_INTERVAL)
            print(f"Manual check triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Create a dummy context object
            class DummyContext:
                def __init__(self, bot):
                    self.bot = bot
            
            dummy_context = DummyContext(application.bot)
            
            # Run the news check
            await check_news_and_alert(dummy_context)
        except Exception as e:
            print(f"Error in manual news check: {e}")
            await asyncio.sleep(60)  # If error, wait a minute and try again

# Data persistence functions
def save_subscribers():
    """Save subscribers to a file"""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subscribers), f)
    print(f"Saved {len(subscribers)} subscribers")

def load_subscribers():
    """Load subscribers from a file"""
    global subscribers
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            subscribers = set(json.load(f))
        print(f"Loaded {len(subscribers)} subscribers")
    except FileNotFoundError:
        subscribers = set()
        print("No subscribers file found, starting with empty set")

def save_user_preferences():
    """Save user preferences to a file"""
    with open(USER_PREFERENCES_FILE, "w") as f:
        json.dump(user_preferences, f)
    print(f"Saved preferences for {len(user_preferences)} users")

def load_user_preferences():
    """Load user preferences from a file"""
    global user_preferences
    try:
        with open(USER_PREFERENCES_FILE, "r") as f:
            user_preferences = json.load(f)
        print(f"Loaded preferences for {len(user_preferences)} users")
    except FileNotFoundError:
        user_preferences = {}
        print("No user preferences file found, starting with empty dict")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("latest", get_latest))
    application.add_handler(CommandHandler("preferences", preferences))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(handle_button))

    # Set up periodic news check (every NEWS_CHECK_INTERVAL seconds) if job queue is available
    try:
        job_queue = application.job_queue
        if job_queue:
            print("Setting up scheduled job queue")
            job_queue.run_repeating(check_news_and_alert, interval=NEWS_CHECK_INTERVAL, first=NEWS_CHECK_INITIAL_DELAY)
            print("Job queue successfully configured")
        else:
            print("Warning: Job queue is not available. Using backup scheduler.")
            # Set up the manual news check
            asyncio.ensure_future(manual_news_check(application))
    except Exception as e:
        print(f"Error setting up job queue: {e}")
        # Set up the manual news check as fallback
        asyncio.ensure_future(manual_news_check(application))

    # Start the Bot
    print(f"Bot starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    application.run_polling()

if __name__ == "__main__":
    print(f"Starting Trump News Alert Bot with Sentiment Analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # Load data when starting
    load_subscribers()
    load_alert_articles()
    load_user_preferences()
    
    try:
        main()
    except KeyboardInterrupt:
        # Save data when shutting down
        save_subscribers()
        save_alert_articles()
        save_user_preferences()
        print("Bot stopped. Data saved.")
