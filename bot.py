import os
import json
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from news_service import fetch_trump_news, load_subscribers, save_subscribers

# Configuration (hidden)


# Track users subscibed to alerts
subscribers = set()

# Track news articles sent in ALERTS only, not for /latest commands
alert_sent_articles = []
last_check_time = datetime.now()


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the bot."""
    user_id = update.effective_user.id
    subscribers.add(user_id)
    
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
    """News request on demand."""
    await update.message.reply_text("Fetching the latest Trump news... ⏳")
    
    # Use for_alerts=False to get ALL recent Trump news without filtering previously sent ones
    articles = await fetch_trump_news(for_alerts=False) #adjusted to send to multiple people without filtering
    
    if not articles:
        await update.message.reply_text("No recent Trump news found. Try again later.") #
        return
    
    # Send up to 5 latest articles
    for article in articles[:5]:
        news_text = f"📰 *{article['title']}*\n\n"
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
                
        news_text += f"\n[Read full article]({article['url']})"
        
        await update.message.reply_text(news_text, parse_mode="Markdown")

# Periodic news check and alert function
async def check_news_and_alert(context: ContextTypes.DEFAULT_TYPE):
    """Check for new Trump news and send alerts to subscribers."""
    if not subscribers:
        return  # No subscribers to alert
    
    # Use for_alerts=True to only get articles we haven't sent alerts for
    articles = await fetch_trump_news(for_alerts=True)
    
    if not articles:
        return  # No new articles
    
    # Send notifications to all subscribers (limit to 3 newest articles)
    for article in articles[:3]:
        news_text = f"🚨 *TRUMP NEWS ALERT*\n\n"
        news_text += f"📰 *{article['title']}*\n\n"
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
                
        news_text += f"\n[Read full article]({article['url']})"
        
        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=news_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Failed to send alert to user {user_id}: {e}")

# Function to manually check news periodically if job queue isn't available
async def manual_news_check(application):
    """Manual implementation of periodic news checks if job queue isn't available"""
    while True:
        # Wait for 15 minutes between checks
        await asyncio.sleep(900)
        
        # Create a dummy context object
        class DummyContext:
            def __init__(self, bot):
                self.bot = bot
        
        dummy_context = DummyContext(application.bot)
        
        # Run the news check
        await check_news_and_alert(dummy_context)

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("latest", get_latest))

    # Set up periodic news check (every 15 minutes) if job queue is available
    try:
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(check_news_and_alert, interval=900, first=10)
        else:
            print("Warning: Job queue is not available. Using backup scheduler.")
            # Set up the manual news check
            import asyncio
            asyncio.ensure_future(manual_news_check(application))
    except Exception as e:
        print(f"Error setting up job queue: {e}")
        # Set up the manual news check as fallback
        import asyncio
        asyncio.ensure_future(manual_news_check(application))

    # Start the Bot
    application.run_polling()


if __name__ == "__main__":
    # Load subscribers when starting
    load_subscribers()
    
    try:
        main()
    except KeyboardInterrupt:
        # Save subscribers when shutting down
        save_subscribers()
        print("Bot stopped. Subscriber list saved.")
