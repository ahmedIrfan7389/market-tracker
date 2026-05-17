import html
import os
import smtplib
from email.mime.text import MIMEText

import requests
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


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

            send_alert(asset["ticker"], up_down, percent_diff, news)

        else:
            print(f"💤 {asset['ticker']} is stable. ({percent_diff:.2f}%)")


def get_asset_news(asset_name):
    params = {
        "q": asset_name,
        "apiKey": NEWS_API_KEY,
        "sortBy": "relevancy",
        "language": "en",
    }
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
    # Prepare the body
    body = f"Significant market activity detected for {symbol}:\n\n"
    for article in news_list:
        body += f"Headline: {html.unescape(article['title'])}\n"
        body += f"Brief: {html.unescape(article['description'] or 'No summary available.')}\n\n"

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"🚨 ALERT: {symbol} {direction} {pct:.2f}%"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


if __name__ == "__main__":
    check_markets()
