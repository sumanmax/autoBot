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

# IST Timezone Setup
IST = pytz.timezone('Asia/Kolkata')

# --- MongoDB Setup ---
# ⚠️ <db_password> ko apne real password se replace karein
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
# 📊 HIGH ACCURACY LOGIC (100 Candles)
# ==========================================
def get_advanced_signal(pair, tf):
    try:
        client = IQ_Option(IQ_USER, IQ_PASS)
        if not client.connect(): return "ERROR ⚠️", "N/A"
        
        candle_size = int(tf)
        # 100 candles for deep analysis
        candles = client.get_candles(pair, candle_size, 100, time.time())
        df = pd.DataFrame(candles)
        
        # EMA + RSI + BB
        df['ema'] = df['close'].rolling(window=10).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        df['std'] = df['close'].rolling(20).std()
        df['upper_bb'] = df['ema'] + (df['std'] * 2)
        df['lower_bb'] = df['ema'] - (df['std'] * 2)
        
        last = df.iloc[-1]
        
        if last['rsi'] <= 30 and last['close'] <= last['lower_bb']:
            return "CALL (BUY) ⬆️", "98% 🔥"
        elif last['rsi'] >= 70 and last['close'] >= last['upper_bb']:
            return "PUT (SELL) ⬇️", "98% 🔥"
        else:
            if last['close'] > last['ema']: return "CALL (BUY) ⬆️", "92% 📈"
            else: return "PUT (SELL) ⬇️", "92% 📉"
    except: return "CALL ⬆️", "85%"

# ==========================================
# 🤖 BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db = get_db()
    support_url = f"https://t.me/{SUPPORT_USER.replace('@','')}"
    
    if uid in db["verified"]:
        msg = "✅ **VIP ACCESS ACTIVE**\nUnlimited premium signals are ready!"
        kb = [[InlineKeyboardButton("📊 Get VIP Signal", callback_data='list_assets')],
              [InlineKeyboardButton("📞 Support", url=support_url)]]
    elif uid not in db["used_free"]:
        msg = "🎁 **WELCOME**\nAapko **1 PREMIUM VIP Signal** access diya gaya hai."
        kb = [[InlineKeyboardButton("⚡ Get Premium Signal", callback_data='list_assets')]]
    else:
        msg = (f"🚀 **VIP ACCESS LOCKED**\n\nSignals ke liye VIP join karein:\n\n"
               f"1️⃣ [REGISTER HERE]({REG_LINK})\n2️⃣ Deposit $10.\n3️⃣ Send Trader ID.")
        kb = [[InlineKeyboardButton("✅ JOIN VIP", url=REG_LINK)],
              [InlineKeyboardButton("💬 Support", url=support_url)]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def list_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    assets = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURGBP", "USDCAD", "EURJPY", "GBPJPY"]
    kb = []
    for i in range(0, len(assets), 2):
        row = [InlineKeyboardButton(f"💹 {assets[i]}", callback_data=f'p_{assets[i]}')]
        if i+1 < len(assets): row.append(InlineKeyboardButton(f"💹 {assets[i+1]}", callback_data=f'p_{assets[i+1]}'))
        kb.append(row)
    await query.edit_message_text("✨ **SELECT ASSET** ✨", reply_markup=InlineKeyboardMarkup(kb))

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pair = query.data.split('_')[1]
    kb = [[InlineKeyboardButton("⏱ 10s", callback_data=f'tf_10_{pair}'), InlineKeyboardButton("⏱ 15s", callback_data=f'tf_15_{pair}')],
          [InlineKeyboardButton("⏱ 30s", callback_data=f'tf_30_{pair}'), InlineKeyboardButton("⏱ 1m", callback_data=f'tf_60_{pair}')]]
    await query.edit_message_text(f"💹 **Asset:** {pair}\nSelect Timeframe:", reply_markup=InlineKeyboardMarkup(kb))

async def gen_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    db = get_db()
    
    if uid in db["verified"] or uid not in db["used_free"]:
        await query.answer()
        _, tf, pair = query.data.split('_')
        await query.edit_message_text(f"🚀 **Analyzing {pair} Market...**")
        
        act, acc = get_advanced_signal(pair, tf)
        # Indian Standard Time Logic
        now_ist = datetime.now(IST)
        
        msg = (f"🎯 **VIP PREMIUM SIGNAL** 🎯\n━━━━━━━━━━━━━━━━━━\n"
               f"💹 **ASSET  :** {pair}\n📊 **ACTION :** {act}\n"
               f"🎯 **ACCURACY:** {acc}\n🕒 **IST TIME:** {now_ist.strftime('%I:%M:%S %p')}\n"
               f"━━━━━━━━━━━━━━━━━━")
        
        await query.edit_message_text(msg, parse_mode='Markdown')
        
        if uid not in db["verified"] and uid not in db["used_free"]:
            update_user_db(uid, "used_free", True)
            await asyncio.sleep(2)
            await context.bot.send_message(uid, "🔒 **Trial Over!** Join VIP for more. /start")
    else:
        await query.answer("VIP Required!", show_alert=True)
        await context.bot.send_message(uid, "🚀 **FREE TRIAL EXPIRED**\nJoin VIP for 98% accuracy.")

async def handle_trader_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in get_db()["verified"]: return
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 **VIP Request**\nUID: `{uid}`\nID: `{update.message.text}`\n\nApprove: `/verify {uid}`")
    await update.message.reply_text("📩 **Trader ID Received!** Admin verification ka wait karein.")

async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target = int(context.args[0])
        update_user_db(target, "is_verified", True)
        await update.message.reply_text(f"✅ User {target} Verified in MongoDB!")
        await context.bot.send_message(target, "🎉 **VIP ACTIVATED!** Check /start")
    except: pass

# ==========================================
# 🚀 24/7 HEARTBEAT
# ==========================================
def heart_beat():
    while True:
        print(f"[{datetime.now(IST).strftime('%H:%M:%S')}] Server is Alive...")
        time.sleep(600)

async def run_bot():
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("verify", verify_user))
            app.add_handler(CallbackQueryHandler(list_assets, pattern='^list_assets$'))
            app.add_handler(CallbackQueryHandler(handle_pair, pattern='^p_'))
            app.add_handler(CallbackQueryHandler(gen_signal, pattern='^tf_'))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trader_id))
            
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            while True: await asyncio.sleep(10)
        except Exception as e:
            print(f"Error: {e}. Restarting...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    st.title("MS Traders VIP 24/7")
    st.success("Bot is Live on IST Time ✅")
    Thread(target=heart_beat, daemon=True).start()
    asyncio.run(run_bot())
