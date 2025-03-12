import os
import json
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from news_service import fetch_trump_news, load_subscribers, save_subscribers
from config import TELEGRAM_TOKEN, CHECK_INTERVAL

# Track users subscibed to alerts
subscribers = set()

# Track news articles sent in ALERTS only, not for /latest commands
alert_sent_articles = []
last_check_time = datetime.now()


# Command handlers
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
    """Send latest Trump news on demand."""
    await update.message.reply_text("Fetching the latest Trump news... ⏳")
    
    # Fetch Trump news articles
    articles = await fetch_trump_news(for_alerts=False)  # Adjusted to send to multiple people without filtering
    
    if not articles:
        await update.message.reply_text("No recent Trump news found. Try again later.")
        return
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Prepare the VOO price message
    voo_message = ""
    if voo_data:
        voo_message = (
            "\n\n📈 *S&P Tracker*\n"
            f"Price: ${voo_data['price']}\n"
            f"Change: {voo_data['change']} ({voo_data['change_percent']})\n"
        )
    else:
        voo_message = "\n\n📈 *VOO Tracker*\nUnable to fetch VOO data at the moment.\n"
    
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
        
        # Append VOO tracker information
        news_text += voo_message
        
        await update.message.reply_text(news_text, parse_mode="Markdown")

# Periodic news check and alert function
async def check_news_and_alert(context: ContextTypes.DEFAULT_TYPE):
    """Check for new Trump news and send alerts to subscribers."""
    if not subscribers:
        return  # No subscribers to alert
    
    # Fetch new Trump news articles
    articles = await fetch_trump_news(for_alerts=True)
    
    if not articles:
        return  # No new articles
    
    # Fetch the latest VOO price
    voo_data = await fetch_voo_price()
    
    # Prepare the VOO price message
    voo_message = ""
    if voo_data:
        voo_message = (
            "\n\n📈 *VOO Tracker*\n"
            f"Price: ${voo_data['price']}\n"
            f"Change: {voo_data['change']} ({voo_data['change_percent']})\n"
        )
    else:
        voo_message = "\n\n📈 *VOO Tracker*\nUnable to fetch VOO data at the moment.\n"
    
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
        
        # Append VOO tracker information
        news_text += voo_message
        
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
