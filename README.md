# @AlertMeeBot
A telegram bot periodically updating with financial news with relation to president Trump. Built in the wake of a volatile market under the Trump Adminstration. Mixing in a little sense in the chaos. 
Access here: t.me/AlertMeeBot

The bot holds no political views or opinions towards the president. 

**Features**
- Periodically fetches the latest news articles related to Donald Trump.
- Uses the Alpha Vantage API to retrieve market-related news.
- Sends updates to a Telegram chat using the Telegram API.
- Can be deployed on a server or run locally for continuous updates.
- On-demand news using the /latest command
- Can support personal chats or group conversations, a little news in your group chat!!

**Commands**
- /start - Subscribe to Trump news alerts
- /stop - Unsubscribe from alerts
- /latest - Get the latest news articles on demand
- /help - Display available commands

**Tech Stack**
- Python: Main programming language
- Telegram API: For sending messages to Telegram
- Alpha Vantage API: For fetching financial and market-related news
- requests: To make HTTP requests
- dotenv: To manage API keys securely

**Future improvements**
- Add live stock alerts tied to each article with real-time prices
- Add additonal sources of news
- Extend beyond trump-related news (maybe Elon)
- Add filtering capability based on keywords
- Implement a web dashboard
- Include sentiment analysis
- Implement stock prediction analysis based off news

**License**
MIT License

**Acknowledgements**
- python-telegram-bot
- Alpha Vantage API

   
