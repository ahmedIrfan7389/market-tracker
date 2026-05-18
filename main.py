import html
import os
import smtplib
import sys
import traceback
from email.mime.text import MIMEText

import requests
import yfinance as yf
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# API keys and credentials loaded from environment variables
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# List of assets to monitor, each with a ticker, name, and alert threshold (% change)
MY_ASSETS = [
    # --- LARGE CAP CRYPTO ---
    # (Threshold 5% because crypto is volatile)
    {"ticker": "BTC-USD", "name": "Bitcoin", "threshold": 5.0},
    {"ticker": "ETH-USD", "name": "Ethereum", "threshold": 5.0},
    {"ticker": "SOL-USD", "name": "Solana", "threshold": 7.0},
    # --- US TECH BIGSHOTS ---
    # (Threshold 3% - these are stable giants)
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "threshold": 3.0},
    {"ticker": "TSLA", "name": "Tesla Inc", "threshold": 3.0},
    {"ticker": "AAPL", "name": "Apple Inc", "threshold": 3.0},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "threshold": 3.0},
    {"ticker": "GOOGL", "name": "Alphabet Inc", "threshold": 3.0},
    # --- PAKISTANI BLUE CHIPS (PSX) ---
    # (Threshold 2% - significant moves in local giants)
    {"ticker": "SYS.KA", "name": "Systems Limited", "threshold": 2.0},
    {"ticker": "LUCK.KA", "name": "Lucky Cement", "threshold": 2.0},
    {"ticker": "HUBC.KA", "name": "Hub Power Company", "threshold": 2.0},
    {"ticker": "MCB.KA", "name": "MCB Bank Limited", "threshold": 2.0},
]


def check_markets():
    """
    Checks the market prices for all assets in MY_ASSETS.
    If the price change exceeds the asset's threshold, fetches related news and sends an alert.
    """
    for asset in MY_ASSETS:
        # 1. Access the Ticker
        ticker = yf.Ticker(asset["ticker"])

        # 2. Fetch last 5 days of market history
        hist = ticker.history(period="5d")

        # 3. Safety Check: If market is closed or data is missing, skip
        if len(hist) < 2:
            print(f"Skipping {asset['ticker']}: Not enough data.")
            continue

        # 4. Pull the closing prices
        # iloc[-1] is the most recent (today/yesterday), iloc[-2] is the day before
        price_today = hist["Close"].iloc[-1]
        price_yesterday = hist["Close"].iloc[-2]

        # 5. Calculate the percentage change
        diff = price_today - price_yesterday
        percent_diff = (diff / price_yesterday) * 100

        up_down = "🔺" if diff > 0 else "🔻"

        if abs(percent_diff) >= asset["threshold"]:
            print(f"🎯 TRIGGER: {asset['ticker']} moved {percent_diff:.2f}%!")

            news = get_asset_news(asset["name"])

            try:
                send_alert(asset["ticker"], up_down, percent_diff, news)
            except Exception as e:
                print(f"Error sending alert for {asset['ticker']}: {e}")
                traceback.print_exc()

        else:
            print(f"💤 {asset['ticker']} is stable. ({percent_diff:.2f}%)")


def get_asset_news(asset_name):
    """
    Fetches the top 3 relevant news articles for a given asset name using NewsAPI.

    Args:
        asset_name (str): The name of the asset to search news for.

    Returns:
        list: A list of news article dictionaries (may be empty if API key is missing or request fails).
    """
    params = {
        "q": asset_name,
        "apiKey": NEWS_API_KEY,
        "sortBy": "relevancy",
        "language": "en",
    }
    if not NEWS_API_KEY:
        print("Warning: NEWS_API_KEY not set — skipping news fetch.")
        return []

    try:
        response = requests.get("https://newsapi.org/v2/everything", params=params)
        response.raise_for_status()
        news_data = response.json()

        return news_data.get("articles", [])[:3]  # Return top 3 articles

    # Catch any exception raised by the requests library (e.g., connection errors, timeouts, invalid responses)
    except requests.RequestException as e:
        print(f"Error fetching news for {asset_name}: {e}")
        return []


def send_alert(symbol, direction, pct, news_list):
    """
    Sends an email alert about significant market activity for a given asset.

    Args:
        symbol (str): The ticker symbol of the asset.
        direction (str): "🔺" for up, "🔻" for down.
        pct (float): Percentage change in price.
        news_list (list): List of news articles to include in the email.
    """
    # Prepare the body
    body = f"Significant market activity detected for {symbol}:\n\n"
    for article in news_list:
        body += f"Headline: {html.unescape(article['title'])}\n"
        body += f"Brief: {html.unescape(article['description'] or 'No summary available.')}\n\n"

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"🚨 ALERT: {symbol} {direction} {pct:.2f}%"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    if not EMAIL_USER or not EMAIL_PASS:
        print("Warning: EMAIL_USER or EMAIL_PASS not set — skipping email send.")
        print("Email body:\n", body)
        return

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


if __name__ == "__main__":
    """
    Entry point: Checks all markets and handles any unhandled exceptions.
    """
    try:
        check_markets()
    except Exception:
        print("Unhandled exception in check_markets:")
        traceback.print_exc()
        sys.exit(1)
