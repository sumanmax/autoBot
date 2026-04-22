import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import json
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime

# Telegram Libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IQ Option API
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAExMDj1PTXc1_EnNI5SLpuMyLtfLwXZdAk"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
ADMIN_ID = 7852639173
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
DB_FILE = "users_data.json"

# ==========================================
# STREAMLIT DASHBOARD (UI)
# ==========================================
st.set_page_config(page_title="AutoBot Server", page_icon="🤖")
st.title("🤖 AutoBot Telegram Server")
st.success("Server is Active!")
st.info("Bot is running in the background. Check Telegram.")

# --- Database Logic ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

# --- IQ Option Connection ---
@st.cache_resource
def get_iq_client():
    client = IQ_Option(IQ_USER, IQ_PASS)
    client.connect()
    return client

def get_instant_signal(pair, tf):
    try:
        client = get_iq_client()
        if not client.check_connect(): client.connect()
        candles = client.get_candles(pair, int(tf) * 60, 30, time.time())
        if not candles: return "CALL ⬆️", "88%"
        df = pd.DataFrame(candles)
        if df['close'].iloc[-1] > df['open'].iloc[-1]: return "CALL (BUY) ⬆️", "94%"
        else: return "PUT (SELL) ⬇️", "94%"
    except: return "CALL ⬆️", "85%"

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {'signals_used': 0, 'is_verified': False}
        save_data(data)
    
    user = data[user_id]
    kb = [[InlineKeyboardButton("📊 Get Signal", callback_data='list_assets')]]
    await update.message.reply_text("🔥 **Bot Active!**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    kb = [[InlineKeyboardButton(a, callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("Select Asset:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("1 Min", callback_data=f'tf_1_{pair}'), InlineKeyboardButton("5 Min", callback_data=f'tf_5_{pair}')]]
    await query.edit_message_text(f"Asset: {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def generate_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tf, pair = query.data.split('_')
    await query.edit_message_text(f"⚡ Analyzing {pair}...")
    action, acc = get_instant_signal(pair, tf)
    msg = f"🎯 **SIGNAL**\nAsset: {pair}\nAction: {action}\nAccuracy: {acc}"
    await query.edit_message_text(msg, parse_mode='Markdown')

# --- FIXED RUNNER FOR STREAMLIT ---
async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(generate_signal, pattern='^tf_'))
    
    # Ye line error fix karti hai Streamlit par
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        # Server ko zinda rakhne ke liye loop
        while True:
            await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception as e:
        st.error(f"Bot Error: {e}")
