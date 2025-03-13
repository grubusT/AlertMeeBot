import os
import json
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Import from our modules
from config import (
    TELEGRAM_TOKEN, SUBSCRIBERS_FILE, NEWS_CHECK_INTERVAL, 
    FIRST_CHECK_DELAY, MAX_ALERTS_PER_CHECK, log_message
)
from news_service import (
    fetch_trump_news, fetch_voo_price, format_article_message,
    load_alert_articles, save_alert_articles
)

# Track users subscribed to alerts
subscribers = set()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bot and subscribe the user."""
    user_id = update.effective_user.id
    subscribers.add(user_id)
    save_subscribers()  # Save after adding subscriber
    
    await update.message.reply_text(
        "👋 Welcome to the Trump News Alert Bot made by Ryan!\n\n"
        "You are now subscribed to Trump news alerts. You'll receive notifications when significant news about Trump is published.\n\n"
        "Commands:\n"
        "/stop - Unsubscribe from alerts\n"
        "/latest - Get the latest Trump news\n"
        "/help - Show available commands"
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
        "/help - Show this help message"
    )

async def get_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send latest Trump news on demand."""
    await update.message.reply_text("Fetching the latest Trump news... ⏳")
    
    # Fetch Trump news articles
    articles = await fetch_trump_news(for_alerts=False)
    
    if not articles:
        await update.message.reply_text("No recent Trump news found. Try again later.")
        return
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Send articles
    for article in articles:
        news_text = format_article_message(article, voo_data, is_alert=False)
        await update.message.reply_text(news_text, parse_mode="Markdown")

# Periodic news check and alert function
async def check_news_and_alert(context: ContextTypes.DEFAULT_TYPE):
    """Check for new Trump news and send alerts to subscribers."""
    log_message("Running scheduled news check")
    
    if not subscribers:
        log_message("No subscribers to alert")
        return  # No subscribers to alert
    
    # Fetch new Trump news articles
    articles = await fetch_trump_news(for_alerts=True)
    
    if not articles:
        log_message("No new articles found")
        return  # No new articles
    
    log_message(f"Found {len(articles)} new articles to send as alerts")
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Send notifications to all subscribers (limit to MAX_ALERTS_PER_CHECK)
    for article in articles[:MAX_ALERTS_PER_CHECK]:
        news_text = format_article_message(article, voo_data, is_alert=True)
        
        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=news_text,
                    parse_mode="Markdown"
                )
                log_message(f"Sent alert to user {user_id}")
            except Exception as e:
                log_message(f"Failed to send alert to user {user_id}: {e}")

# Function to manually check news periodically if job queue isn't available
async def manual_news_check(application):
    """Manual implementation of periodic news checks if job queue isn't available"""
    log_message("Starting manual news checker backup system")
    while True:
        try:
            # Wait between checks
            await asyncio.sleep(NEWS_CHECK_INTERVAL)
            log_message("Manual check triggered")
            
            # Create a dummy context object
            class DummyContext:
                def __init__(self, bot):
                    self.bot = bot
            
            dummy_context = DummyContext(application.bot)
            
            # Run the news check
            await check_news_and_alert(dummy_context)
        except Exception as e:
            log_message(f"Error in manual news check: {e}")
            await asyncio.sleep(60)  # If error, wait a minute and try again

def save_subscribers():
    """Save subscribers to a file"""
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subscribers), f)
    log_message(f"Saved {len(subscribers)} subscribers")

def load_subscribers():
    """Load subscribers from a file"""
    global subscribers
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            subscribers = set(json.load(f))
        log_message(f"Loaded {len(subscribers)} subscribers")
    except FileNotFoundError:
        subscribers = set()
        log_message("No subscribers file found, starting with empty set")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("latest", get_latest))

    # Set up periodic news check
    try:
        job_queue = application.job_queue
        if job_queue:
            log_message("Setting up scheduled job queue")
            job_queue.run_repeating(check_news_and_alert, interval=NEWS_CHECK_INTERVAL, first=FIRST_CHECK_DELAY)
            log_message("Job queue successfully configured")
        else:
            log_message("Warning: Job queue is not available. Using backup scheduler.")
            # Set up the manual news check
            asyncio.ensure_future(manual_news_check(application))
    except Exception as e:
        log_message(f"Error setting up job queue: {e}")
        # Set up the manual news check as fallback
        asyncio.ensure_future(manual_news_check(application))

    # Start the Bot
    log_message("Bot starting")
    application.run_polling()


if __name__ == "__main__":
    log_message("Starting Trump News Alert Bot")
    # Load subscribers and article history when starting
    load_subscribers()
    load_alert_articles()
    
    try:
        main()
    except KeyboardInterrupt:
        # Save subscribers when shutting down
        save_subscribers()
        save_alert_articles()
        log_message("Bot stopped. Subscriber list and article history saved.")
