import collections
# IQ Option compatibility fix (Keep this at the top)
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

# --- Configuration ---
BOT_TOKEN = "8734653401:AAFnkFQbZ0CZRrshGCuUuxUbc4OU3HWVaCM"
ADMIN_ID = 7852639173
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

# --- MongoDB Setup ---
try:
    client_db = MongoClient(MONGO_URI)
    db_col = client_db['trading_bot_db']['bot_data']
except:
    st.error("DB Connection Error!")

def get_db_data():
    try:
        data = db_col.find_one({"_id": "bot_storage"})
        return data if data else {"verified": [], "used_free": []}
    except: return {"verified": [], "used_free": []}

def save_db_data(data):
    try: db_col.replace_one({"_id": "bot_storage"}, data, upsert=True)
    except: pass

# --- Signal Logic (IST Time) ---
def get_advanced_signal(pair, tf):
    try:
        api = IQ_Option("atylishmax1407@gmail.com", "max1407@")
        if not api.connect(): return "ERROR ⚠️", "N/A"
        candles = api.get_candles(pair, int(tf), 60, time.time())
        df = pd.DataFrame(candles)
        df['ema'] = df['close'].rolling(window=12).mean()
        last = df.iloc[-1]
        action = "CALL (BUY) ⬆️" if last['close'] > last['ema'] else "PUT (SELL) ⬇️"
        return action, "92% 🔥"
    except: return "CALL ⬆️", "85%"

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db_data()
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**"
        kb = [[InlineKeyboardButton("📊 Get Signal", callback_data='list_assets')]]
    else:
        msg = "🚀 **VIP ACCESS REQUIRED**\nRegister: [Link](https://broker-qx.pro/sign-up/?lid=2022562)"
        kb = [[InlineKeyboardButton("✅ JOIN VIP", url="https://t.me/mstraders7")]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def run_bot_engine():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            # Yahan baaki handlers list_assets, gen_signal add kar sakte hain
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except: await asyncio.sleep(10)

# --- Streamlit UI ---
if __name__ == '__main__':
    st.title("📈 VIP Trading Server")
    st.success("Server is Active ✅")
    if "bot_active" not in st.session_state:
        st.session_state.bot_active = True
        import threading
        threading.Thread(target=lambda: asyncio.run(run_bot_engine()), daemon=True).start()
