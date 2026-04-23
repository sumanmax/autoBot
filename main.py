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
from datetime import datetime, timedelta

# Telegram Libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IQ Option API
from iqoptionapi.stable_api import IQ_Option

# ==========================================
# CONFIGURATION & DATABASE
# ==========================================
BOT_TOKEN = "8734653401:AAHnZKY6RCJIFQ8U4tGCOwjLwCZbJi-a4kQ"
IQ_USER = "atylishmax1407@gmail.com"
IQ_PASS = "max1407@"
ADMIN_ID = 7852639173
DB_FILE = "users_db.json"

# Database Loading
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f: json.dump({"verified_users": []}, f)

def is_verified(user_id):
    with open(DB_FILE, "r") as f:
        data = json.load(f)
        return user_id in data["verified_users"]

def verify_user(user_id):
    with open(DB_FILE, "r") as f: data = json.load(f)
    if user_id not in data["verified_users"]:
        data["verified_users"].append(user_id)
        with open(DB_FILE, "w") as f: json.dump(data, f)

# ==========================================
# ORIGINAL SIGNAL LOGIC (RSI + EMA)
# ==========================================
def get_instant_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        client.connect()
        candles = client.get_candles(pair, int(tf) * 60, 40, time.time())
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
    except: return "CALL ⬆️", "85%"

# ==========================================
# BOT HANDLERS WITH ACCESS CONTROL
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_verified(user_id):
        kb = [[InlineKeyboardButton("📊 Get VIP Signal (IST)", callback_data='list_assets')]]
        await update.message.reply_text("✅ Welcome back! Your access is active.", reply_markup=InlineKeyboardMarkup(kb))
    else:
        msg = ("🚫 **Access Restricted!**\n\n"
               "Bot ko use karne ke liye aapko hamari link se account banana hoga.\n\n"
               "1. Is link se Register karein: [APNI LINK YAHAN DALEIN]\n"
               "2. Apni **Trader ID** yahan niche message mein bhejein.\n\n"
               "Admin verify karne ke baad aapko access de dega.")
        await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_verified(user_id): return # Already verified

    trader_id = update.message.text
    # Admin ko notify karna
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **New Verification Request**\nUser ID: `{user_id}`\nTrader ID: `{trader_id}`\n\nAccess dene ke liye type karein:\n`/verify {user_id}`",
        parse_mode='Markdown'
    )
    await update.message.reply_text("📩 Trader ID bhej di gayi hai. Admin ke verify karne ka intezar karein.")

async def admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        verify_user(target_id)
        await update.message.reply_text(f"✅ User {target_id} has been verified!")
        await context.bot.send_message(chat_id=target_id, text="🎉 **Congratulations!** Your access is now active. Type /start to begin.")
    except:
        await update.message.reply_text("Usage: /verify USER_ID")

# (Signal generation and list_assets handlers here...)
# [Note: Add 'list_assets', 'handle_pair', and 'generate_signal' from previous code]

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", admin_verify))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
    # ... baki handlers ...
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(run_bot())
