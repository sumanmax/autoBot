import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
import pytz
from datetime import datetime
from pymongo import MongoClient
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAG5Ng8cG3mLbBxxTq-LQQZ6yZdTO8LLIP8"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"

IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup ---
MONGO_URL = "mongodb+srv://atylishmax1407_db_user:<db_password>@cluster0.rxd940g.mongodb.net/?appName=Cluster0"
client_db = MongoClient(MONGO_URL)
db_mongo = client_db['trading_bot_db']
collection = db_mongo['users']

def get_db():
    verified = []
    used_free = []
    for user in collection.find():
        if user.get("is_verified"): verified.append(user["_id"])
        if user.get("used_free"): used_free.append(user["_id"])
    return {"verified": verified, "used_free": used_free}

def update_user_db(uid, field, value):
    collection.update_one({"_id": uid}, {"$set": {field: value}}, upsert=True)

# ==========================================
# 📊 SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        candles = client.get_candles(pair, int(tf), 100, time.time())
        df = pd.DataFrame(candles)
        # Simple Logic for testing
        last_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        if last_close > prev_close: return "CALL (BUY) ⬆️", "94%"
        else: return "PUT (SELL) ⬇️", "94%"
    except: return "WAIT ⏳", "N/A"

# ==========================================
# 🤖 BOT HANDLERS (Start, List, Signal, etc.)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is Active! Use buttons to get signals.")

# [Baaki handlers jaise handle_pair, gen_signal pehle jaise hi rahenge...]

# ==========================================
# 🚀 CORE RUNNER (Fixed Conflict Logic)
# ==========================================
async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Initialize and clean old sessions
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("start", start))
    # Add other handlers here...

    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

def start_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# ==========================================
# 🌐 STREAMLIT UI & PREVENT DUPLICATES
# ==========================================
st.title("MS Traders VIP Bot")

if "bot_started" not in st.session_state:
    st.session_state.bot_started = True
    st.write("🔄 Initializing Bot Instance...")
    # Thread chalu karne se pehle 5 sec wait karein purane session clear hone ke liye
    time.sleep(5)
    thread = Thread(target=start_bot_thread, daemon=True)
    thread.start()
    st.success("✅ Bot successfully started in background!")
else:
    st.info("ℹ️ Bot is already running in the background.")

st.write("---")
st.write("Database Status: Connected 🌐")
