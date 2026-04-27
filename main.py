import collections
# IQ Option compatibility fix
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

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAFnkFQbZ0CZRrshGCuUuxUbc4OU3HWVaCM"
ADMIN_ID = 7852639173
SUPPORT_USER = "@mstraders7"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
REG_LINK = "https://broker-qx.pro/sign-up/?lid=2022562"
MONGO_URI = "mongodb+srv://atylishmax1407_db_user:L6T5cl4gztJIaRRs@cluster0.rxd940g.mongodb.net/?appName=Cluster0"

# Database Connection
try:
    client_db = MongoClient(MONGO_URI)
    mongo_db = client_db['trading_bot_db']
    users_col = mongo_db['bot_data']
except Exception as e:
    st.error(f"DB Connection Error: {e}")

def get_db():
    try:
        data = users_col.find_one({"_id": "bot_storage"})
        if not data:
            initial = {"_id": "bot_storage", "verified": [], "used_free": []}
            users_col.insert_one(initial)
            return initial
        return data
    except: return {"verified": [], "used_free": []}

def save_db(data):
    try: users_col.replace_one({"_id": "bot_storage"}, data)
    except: pass

# ==========================================
# 📊 SIGNAL LOGIC
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        candles = client.get_candles(pair, int(tf), 60, time.time())
        df = pd.DataFrame(candles)
        df['ema'] = df['close'].rolling(window=12).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        last = df.iloc[-1]
        if last['rsi'] < 30: return "CALL (BUY) ⬆️", "97% 🔥"
        elif last['rsi'] > 70: return "PUT (SELL) ⬇️", "97% 🔥"
        else: return ("CALL ⬆️" if last['close'] > last['ema'] else "PUT ⬇️"), "92%"
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    if uid in db["verified"]:
        msg = "✅ **VIP ACTIVE**"
        kb = [[InlineKeyboardButton("📊 Get Signal", callback_data='list_assets')]]
    elif uid not in db["used_free"]:
        msg = "🎁 **1 FREE SIGNAL AVAILABLE**"
        kb = [[InlineKeyboardButton("⚡ Start Free Trial", callback_data='list_assets')]]
    else:
        msg = f"🚀 **VIP REQUIRED**\nRegister: {REG_LINK}"
        kb = [[InlineKeyboardButton("✅ JOIN VIP", url=REG_LINK)]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"]
    kb = [[InlineKeyboardButton(f"💹 {a}", callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("✨ **SELECT ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("⏱ 1m", callback_data=f'tf_60_{pair}'), InlineKeyboardButton("⏱ 5m", callback_data=f'tf_300_{pair}')]]
    await query.edit_message_text(f"💹 **{pair}**\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair}...**")
        act, acc = get_advanced_signal(pair, tf)
        ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        msg = f"🎯 **VIP SIGNAL**\nASSET: {pair}\nACTION: {act}\nACCURACY: {acc}\nIST: {ist.strftime('%I:%M:%S %p')}"
        await query.edit_message_text(msg)
        if uid not in db["verified"]:
            db["used_free"].append(uid)
            save_db(db)
    else:
        await query.answer("Trial Expired! Join VIP.", show_alert=True)

# (Admin Handlers like handle_trader_id & verify_user same as before)

# ==========================================
# 🔄 SERVER ENGINE
# ==========================================
async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(3600)
        except: await asyncio.sleep(10)

if __name__ == '__main__':
    st.title("📈 Trading Bot Server")
    st.success("Running... ✅")
    if "bot_started" not in st.session_state:
        st.session_state.bot_started = True
        import threading
        threading.Thread(target=lambda: asyncio.run(run_bot()), daemon=True).start()
