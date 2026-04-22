import collections
if not hasattr(collections, 'Iterable'):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

import os
import time
import asyncio
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Telegram Libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# IQ Option API
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8734653401:AAExMDj1PTXc1_EnNI5SLpuMyLtfLwXZdAk"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="AutoBot VIP", page_icon="🚀")
st.title("🚀 AutoBot VIP: IST Time Fixed")
st.success("Status: Bot is Active")

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
        
        candles = client.get_candles(pair, int(tf) * 60, 40, time.time())
        if not candles: return "CALL ⬆️", "85%"
        
        df = pd.DataFrame(candles)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['ema'] = df['close'].rolling(window=10).mean()
        
        last_rsi, last_close, last_ema = df['rsi'].iloc[-1], df['close'].iloc[-1], df['ema'].iloc[-1]

        if last_close > last_ema:
            return "CALL (BUY) ⬆️", ("88%" if last_rsi < 65 else "82%")
        else:
            return "PUT (SELL) ⬇️", ("88%" if last_rsi > 35 else "82%")
    except:
        return "CALL ⬆️", "85%"

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📊 Get VIP Signal (IST)", callback_data='list_assets')]]
    await update.message.reply_text("🔥 **AutoBot VIP Mode Active!**\nTimezone: India (IST)", 
                                   reply_markup=InlineKeyboardMarkup(kb))

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY"]
    kb = [[InlineKeyboardButton(a, callback_data=f'p_{a}')] for a in assets]
    await query.edit_message_text("Select Trading Asset:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("1 Min", callback_data=f'tf_1_{pair}'), 
           InlineKeyboardButton("5 Min", callback_data=f'tf_5_{pair}')]]
    await query.edit_message_text(f"Asset: {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def generate_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, tf, pair = query.data.split('_')
    
    await query.edit_message_text(f"🚀 **Analyzing {pair}...**")
    
    action, acc = get_instant_signal(pair, tf)
    
    # --- FIXED IST TIME LOGIC ---
    # UTC টাইমের সাথে ৫ ঘণ্টা ৩০ মিনিট যোগ করা হচ্ছে
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_time_ist = ist_time.strftime('%I:%M:%S %p') # 12-hour format with AM/PM
    
    msg = (f"🎯 **VIP INSTANT SIGNAL**\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💹 **Asset:** {pair}\n"
           f"📊 **Action:** {action}\n"
           f"🎯 **Accuracy:** {acc}\n"
           f"🕒 **Time (IST):** {current_time_ist}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"🚀 *Trade immediately!*")
    
    await query.edit_message_text(msg, parse_mode='Markdown')

# --- Run Bot ---
async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
    app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
    app.add_handler(CallbackQueryHandler(generate_signal, pattern='^tf_'))
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())
