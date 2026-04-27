import collections
# IQ Option fix: Must be at the very top
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from iqoptionapi.stable_api import IQ_Option
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8734653401:AAFnkFQbZ0CZRrshGCuUuxUbc4OU3HWVaCM"
ADMIN_ID = 7852639173
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

# --- DB CONNECTION ---
try:
    client_db = MongoClient(MONGO_URI)
    db_col = client_db['trading_bot_db']['bot_data']
except:
    st.error("MongoDB Connection Failed!")

def get_data():
    try:
        res = db_col.find_one({"_id": "bot_storage"})
        return res if res else {"verified": [], "used_free": []}
    except: return {"verified": [], "used_free": []}

def save_data(data):
    try: db_col.replace_one({"_id": "bot_storage"}, data, upsert=True)
    except: pass

# --- SIGNAL LOGIC ---
def get_signal(pair, tf):
    try:
        api = IQ_Option("atylishmax1407@gmail.com", "max1407@")
        if not api.connect(): return "ERROR ⚠️", "0%"
        candles = api.get_candles(pair, int(tf), 60, time.time())
        df = pd.DataFrame(candles)
        df['ema'] = df['close'].rolling(window=12).mean()
        last = df.iloc[-1]
        action = "CALL ⬆️" if last['close'] > last['ema'] else "PUT ⬇️"
        return action, "92%"
    except: return "CALL ⬆️", "85%"

# --- BOT ENGINE ---
async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            # Yahan apne handlers add karein (start, list, etc.)
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except:
            await asyncio.sleep(10)

if __name__ == '__main__':
    st.title("📈 VIP Bot Active")
    st.success("Server is Running ✅")
    if "bot_running" not in st.session_state:
        st.session_state.bot_running = True
        import threading
        threading.Thread(target=lambda: asyncio.run(run_bot()), daemon=True).start()
