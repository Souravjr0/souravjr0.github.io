#!/usr/bin/env python3
"""
Helper script to get your Telegram chat ID.

Instructions:
1. Run this script: python get_telegram_chat_id.py
2. Send a message to your bot on Telegram (anything works, e.g., "hi")
3. The script will display your chat ID
4. Copy the chat ID and paste it into .env as TELEGRAM_CHAT_ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    print("Add your bot token to .env and try again.")
    exit(1)

print(f"✅ Bot token found: {TOKEN[:20]}...")
print("\n📱 Now send a message to your bot on Telegram!")
print("Then press ENTER to fetch your chat ID...")

input()

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()
    
    if data.get("ok") and data.get("result"):
        for update in data["result"]:
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                print(f"\n✅ Your Telegram Chat ID: {chat_id}")
                print(f"\n📝 Add this to your .env file:")
                print(f"TELEGRAM_CHAT_ID={chat_id}")
                break
        else:
            print("❌ No messages found. Make sure you sent a message to the bot first.")
    else:
        print("❌ Failed to fetch updates. Check your token and try again.")
        print(f"Response: {data}")
except Exception as e:
    print(f"❌ Error: {e}")
